"""SQLAlchemy schema and engine factory for the persistent store.

This module is intentionally database-agnostic: it only uses portable column
types (``String``, ``Integer``, ``Boolean``, ``JSON``) and a small engine
factory keyed off the URL scheme. SQLite is the default target, but the same
ORM models work against Postgres et al. — only the ``DATABASE_URL`` changes.

Nothing here touches the filesystem or opens a connection at import time; an
engine is created only when :func:`make_engine` is called (i.e. when a
``DATABASE_URL`` is configured).
"""

from sqlalchemy import JSON, Boolean, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)


class TokenTable(Base):
    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)


class ScoreTable(Base):
    __tablename__ = "scores"

    # Surrogate autoincrement id; the API exposes it as ``score_<id>`` to keep
    # the same shape the in-memory store produced.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)


class ActiveGameTable(Base):
    __tablename__ = "active_games"

    # One live game per user, so the user id is the primary key (upsert target).
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)
    # Pinned games are exempt from stale-pruning (used for demo/seed games).
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


def make_engine(url: str) -> Engine:
    """Build an engine for ``url``, applying SQLite-specific connection tweaks.

    The tweaks are confined to the ``sqlite`` scheme so other databases get a
    vanilla engine. ``check_same_thread=False`` is required because FastAPI runs
    sync endpoints across a thread pool; an in-memory SQLite URL additionally
    needs :class:`StaticPool` so every connection shares the one database.
    """
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if url == "sqlite://" or ":memory:" in url:
            return create_engine(
                url, connect_args=connect_args, poolclass=StaticPool
            )
        return create_engine(url, connect_args=connect_args)
    return create_engine(url)
