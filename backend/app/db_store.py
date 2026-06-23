"""SQLAlchemy-backed store.

A drop-in replacement for the in-memory :class:`app.store.Store` that persists
to a real database. It exposes the exact same method surface so the routers are
agnostic to which backend is active (see :mod:`app.storage`).

Unlike the in-memory store, this one is *persistent*: ``reset`` only ensures the
schema exists (it does not wipe data) and ``seed`` is a no-op — the database
keeps whatever real users and games have accumulated across restarts.
"""

from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .db import ActiveGameTable, Base, ScoreTable, TokenTable, UserTable, make_engine
from .models import ActiveGame, GameMode, GameState, ScoreEntry
from .security import generate_token, hash_password
from .store import STALE_MS, UserRecord, now_ms


class DbStore:
    def __init__(self, database_url: str) -> None:
        self.engine = make_engine(database_url)
        self._session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False
        )
        # Ensure the schema exists up front so the very first request works.
        self.reset()

    def _session(self) -> Session:
        return self._session_factory()

    # ---- lifecycle ------------------------------------------------------

    def reset(self) -> None:
        """Ensure the schema exists. Non-destructive — existing rows are kept."""
        Base.metadata.create_all(self.engine)

    def seed(self) -> None:
        """No-op: seed data lives only in the in-memory/demo store."""

    # ---- row -> model converters ---------------------------------------

    @staticmethod
    def _to_user_record(row: UserTable) -> UserRecord:
        return UserRecord(
            id=row.id, username=row.username, password_hash=row.password_hash
        )

    @staticmethod
    def _to_score_entry(row: ScoreTable) -> ScoreEntry:
        return ScoreEntry(
            id=f"score_{row.id}",
            userId=row.user_id,
            username=row.username,
            mode=row.mode,
            score=row.score,
            createdAt=row.created_at,
        )

    @staticmethod
    def _to_active_game(row: ActiveGameTable) -> ActiveGame:
        return ActiveGame(
            userId=row.user_id,
            username=row.username,
            mode=row.mode,
            score=row.score,
            state=GameState(**row.state),
            updatedAt=row.updated_at,
        )

    # ---- users ----------------------------------------------------------

    def create_user(
        self, username: str, password: str, *, user_id: Optional[str] = None
    ) -> UserRecord:
        uid = user_id or f"usr_{generate_token()[:12]}"
        password_hash = hash_password(password)
        with self._session() as session:
            session.add(
                UserTable(id=uid, username=username, password_hash=password_hash)
            )
            session.commit()
        return UserRecord(id=uid, username=username, password_hash=password_hash)

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        with self._session() as session:
            row = session.get(UserTable, user_id)
            return self._to_user_record(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        with self._session() as session:
            row = session.scalars(
                select(UserTable).where(
                    func.lower(UserTable.username) == username.lower()
                )
            ).first()
            return self._to_user_record(row) if row else None

    # ---- tokens ---------------------------------------------------------

    def issue_token(self, user_id: str) -> str:
        token = generate_token()
        with self._session() as session:
            session.add(TokenTable(token=token, user_id=user_id))
            session.commit()
        return token

    def revoke_token(self, token: str) -> None:
        with self._session() as session:
            session.execute(delete(TokenTable).where(TokenTable.token == token))
            session.commit()

    def user_for_token(self, token: str) -> Optional[UserRecord]:
        with self._session() as session:
            tok = session.get(TokenTable, token)
            if tok is None:
                return None
            row = session.get(UserTable, tok.user_id)
            return self._to_user_record(row) if row else None

    # ---- scores ---------------------------------------------------------

    def add_score(
        self, user_id: str, username: str, mode: GameMode, score: int
    ) -> ScoreEntry:
        with self._session() as session:
            row = ScoreTable(
                user_id=user_id,
                username=username,
                mode=mode.value,
                score=score,
                created_at=now_ms(),
            )
            session.add(row)
            session.commit()
            return self._to_score_entry(row)

    def leaderboard(self, mode: GameMode, limit: int = 10) -> list[ScoreEntry]:
        """Best score per user for a mode, sorted by score descending."""
        with self._session() as session:
            rows = session.scalars(
                select(ScoreTable).where(ScoreTable.mode == mode.value)
            ).all()
        best: dict[str, ScoreTable] = {}
        for row in rows:
            current = best.get(row.user_id)
            if current is None or row.score > current.score:
                best[row.user_id] = row
        ranked = sorted(best.values(), key=lambda r: r.score, reverse=True)
        return [self._to_score_entry(r) for r in ranked[:limit]]

    # ---- active games ---------------------------------------------------

    def publish_game(
        self,
        user_id: str,
        username: str,
        state: GameState,
        mode: GameMode,
        score: int,
    ) -> ActiveGame:
        timestamp = now_ms()
        with self._session() as session:
            row = session.get(ActiveGameTable, user_id)
            if row is None:
                session.add(
                    ActiveGameTable(
                        user_id=user_id,
                        username=username,
                        mode=mode.value,
                        score=score,
                        state=state.model_dump(mode="json"),
                        updated_at=timestamp,
                        pinned=False,
                    )
                )
            else:
                # Upsert: refresh the game but keep its pinned flag.
                row.username = username
                row.mode = mode.value
                row.score = score
                row.state = state.model_dump(mode="json")
                row.updated_at = timestamp
            session.commit()
        return ActiveGame(
            userId=user_id,
            username=username,
            mode=mode,
            score=score,
            state=state,
            updatedAt=timestamp,
        )

    def end_game(self, user_id: str) -> None:
        with self._session() as session:
            session.execute(
                delete(ActiveGameTable).where(ActiveGameTable.user_id == user_id)
            )
            session.commit()

    def prune(self) -> bool:
        """Remove stale (non-pinned) games. Returns True if anything was removed."""
        cutoff = now_ms() - STALE_MS
        with self._session() as session:
            result = session.execute(
                delete(ActiveGameTable).where(
                    ActiveGameTable.pinned.is_(False),
                    ActiveGameTable.updated_at < cutoff,
                )
            )
            session.commit()
            return result.rowcount > 0

    def list_active_games(self) -> list[ActiveGame]:
        self.prune()
        with self._session() as session:
            rows = session.scalars(
                select(ActiveGameTable).order_by(ActiveGameTable.score.desc())
            ).all()
            return [self._to_active_game(row) for row in rows]

    def get_active_game(self, user_id: str) -> Optional[ActiveGame]:
        self.prune()
        with self._session() as session:
            row = session.get(ActiveGameTable, user_id)
            return self._to_active_game(row) if row else None
