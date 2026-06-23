"""In-memory data store with seed data.

A single process-wide :class:`Store` instance (``store``) holds everything: users,
session tokens, submitted scores, and live ("active") games. There is no database
yet — restarting the server resets all state back to the seed.
"""

import time
from dataclasses import dataclass
from typing import Optional

from .models import ActiveGame, Direction, GameMode, GameState, ScoreEntry
from .security import generate_token, hash_password

# An active game is considered stale (and pruned) if it has not been updated
# within this window. Seeded demo games are "pinned" and exempt from pruning so
# the frontend always has something to show.
STALE_MS = 30_000


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class UserRecord:
    """Internal user record. Never serialized directly (holds the password hash)."""

    id: str
    username: str
    password_hash: str


class Store:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.users: dict[str, UserRecord] = {}
        self._username_index: dict[str, str] = {}  # lowercased username -> user id
        self.tokens: dict[str, str] = {}  # token -> user id
        self.scores: list[ScoreEntry] = []
        self.active_games: dict[str, ActiveGame] = {}  # user id -> game
        self.pinned: set[str] = set()  # user ids exempt from stale-pruning
        self._score_seq = 0

    # ---- users ----------------------------------------------------------

    def create_user(
        self, username: str, password: str, *, user_id: Optional[str] = None
    ) -> UserRecord:
        uid = user_id or f"usr_{generate_token()[:12]}"
        record = UserRecord(id=uid, username=username, password_hash=hash_password(password))
        self.users[uid] = record
        self._username_index[username.lower()] = uid
        return record

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        uid = self._username_index.get(username.lower())
        return self.users.get(uid) if uid else None

    # ---- tokens ---------------------------------------------------------

    def issue_token(self, user_id: str) -> str:
        token = generate_token()
        self.tokens[token] = user_id
        return token

    def revoke_token(self, token: str) -> None:
        self.tokens.pop(token, None)

    def user_for_token(self, token: str) -> Optional[UserRecord]:
        uid = self.tokens.get(token)
        return self.users.get(uid) if uid else None

    # ---- scores ---------------------------------------------------------

    def add_score(
        self, user_id: str, username: str, mode: GameMode, score: int
    ) -> ScoreEntry:
        self._score_seq += 1
        entry = ScoreEntry(
            id=f"score_{self._score_seq}",
            userId=user_id,
            username=username,
            mode=mode,
            score=score,
            createdAt=now_ms(),
        )
        self.scores.append(entry)
        return entry

    def leaderboard(self, mode: GameMode, limit: int = 10) -> list[ScoreEntry]:
        """Best score per user for a mode, sorted by score descending."""
        best: dict[str, ScoreEntry] = {}
        for entry in self.scores:
            if entry.mode != mode:
                continue
            current = best.get(entry.userId)
            if current is None or entry.score > current.score:
                best[entry.userId] = entry
        ranked = sorted(best.values(), key=lambda e: e.score, reverse=True)
        return ranked[:limit]

    # ---- active games ---------------------------------------------------

    def publish_game(
        self,
        user_id: str,
        username: str,
        state: GameState,
        mode: GameMode,
        score: int,
    ) -> ActiveGame:
        game = ActiveGame(
            userId=user_id,
            username=username,
            mode=mode,
            score=score,
            state=state,
            updatedAt=now_ms(),
        )
        self.active_games[user_id] = game
        return game

    def end_game(self, user_id: str) -> None:
        self.active_games.pop(user_id, None)

    def prune(self) -> bool:
        """Remove stale (non-pinned) games. Returns True if anything was removed."""
        cutoff = now_ms() - STALE_MS
        stale = [
            uid
            for uid, game in self.active_games.items()
            if uid not in self.pinned and game.updatedAt < cutoff
        ]
        for uid in stale:
            del self.active_games[uid]
        return bool(stale)

    def list_active_games(self) -> list[ActiveGame]:
        self.prune()
        return sorted(self.active_games.values(), key=lambda g: g.score, reverse=True)

    def get_active_game(self, user_id: str) -> Optional[ActiveGame]:
        self.prune()
        return self.active_games.get(user_id)

    # ---- seeding --------------------------------------------------------

    def seed(self) -> None:
        """Populate the store with fake users, scores, and active games."""
        seed_users = [
            ("usr_alice", "alice", "password1"),
            ("usr_bob", "bob", "password2"),
            ("usr_carol", "carol", "hunter22"),
            ("usr_dave", "dave", "snakey99"),
        ]
        for uid, username, password in seed_users:
            self.create_user(username, password, user_id=uid)

        seed_scores = [
            ("usr_alice", GameMode.walls, 42),
            ("usr_alice", GameMode.walls, 58),
            ("usr_alice", GameMode.wrap, 31),
            ("usr_bob", GameMode.walls, 37),
            ("usr_bob", GameMode.wrap, 64),
            ("usr_bob", GameMode.wrap, 50),
            ("usr_carol", GameMode.walls, 73),
            ("usr_carol", GameMode.wrap, 45),
            ("usr_dave", GameMode.walls, 19),
            ("usr_dave", GameMode.wrap, 88),
        ]
        for uid, mode, score in seed_scores:
            self.add_score(uid, self.users[uid].username, mode, score)

        self.publish_game(
            "usr_alice",
            "alice",
            GameState(
                width=20,
                height=20,
                snake=[(10, 10), (10, 11), (10, 12)],
                food=(5, 5),
                dir=Direction.up,
                alive=True,
            ),
            GameMode.walls,
            58,
        )
        self.publish_game(
            "usr_carol",
            "carol",
            GameState(
                width=20,
                height=20,
                snake=[(3, 3), (4, 3)],
                food=(15, 9),
                dir=Direction.right,
                alive=True,
            ),
            GameMode.wrap,
            45,
        )
        # Keep the seeded games visible indefinitely for the demo.
        self.pinned = {"usr_alice", "usr_carol"}


# Process-wide singleton used by the routers.
store = Store()
