"""Direct integration tests for the SQLAlchemy-backed ``DbStore``.

These talk to a real database (in-memory SQLite, plus a temp file for the
persistence check) through the actual ORM layer — no API and no mocking.
"""

from app.db import ActiveGameTable
from app.db_store import DbStore
from app.models import Direction, GameMode, GameState
from app.store import STALE_MS, now_ms


def _state() -> GameState:
    return GameState(
        width=20,
        height=20,
        snake=[(1, 1), (1, 2)],
        food=(9, 3),
        dir=Direction.down,
        alive=True,
    )


# ---- users --------------------------------------------------------------


def test_create_and_fetch_user(db_store):
    rec = db_store.create_user("Alice", "password1", user_id="usr_a")
    assert rec.id == "usr_a"
    assert db_store.get_user("usr_a").username == "Alice"
    # Password is stored hashed, never in plaintext.
    assert rec.password_hash.startswith("pbkdf2_sha256$")
    assert rec.password_hash != "password1"


def test_get_user_by_username_is_case_insensitive(db_store):
    db_store.create_user("Dupe", "password1", user_id="usr_d")
    assert db_store.get_user_by_username("dupe").id == "usr_d"
    assert db_store.get_user_by_username("DUPE").id == "usr_d"


def test_get_unknown_user_returns_none(db_store):
    assert db_store.get_user("nope") is None
    assert db_store.get_user_by_username("nobody") is None


# ---- tokens -------------------------------------------------------------


def test_token_issue_lookup_and_revoke(db_store):
    user = db_store.create_user("bob", "password2", user_id="usr_b")
    token = db_store.issue_token(user.id)
    assert db_store.user_for_token(token).id == "usr_b"

    db_store.revoke_token(token)
    assert db_store.user_for_token(token) is None


def test_unknown_token_returns_none(db_store):
    assert db_store.user_for_token("not-a-real-token") is None


# ---- scores -------------------------------------------------------------


def test_add_score_returns_persisted_entry(db_store):
    entry = db_store.add_score("usr_a", "alice", GameMode.walls, 42)
    assert entry.id.startswith("score_")
    assert entry.userId == "usr_a"
    assert entry.mode == GameMode.walls
    assert entry.score == 42
    assert entry.createdAt > 0


def test_leaderboard_best_per_user_sorted_and_limited(db_store):
    db_store.add_score("usr_a", "alice", GameMode.walls, 42)
    db_store.add_score("usr_a", "alice", GameMode.walls, 58)  # alice's best
    db_store.add_score("usr_b", "bob", GameMode.walls, 37)
    db_store.add_score("usr_c", "carol", GameMode.walls, 73)
    db_store.add_score("usr_a", "alice", GameMode.wrap, 99)  # different mode

    board = db_store.leaderboard(GameMode.walls)
    scores = [e.score for e in board]
    assert scores == sorted(scores, reverse=True)
    usernames = [e.username for e in board]
    assert len(usernames) == len(set(usernames))  # one entry per user
    alice = next(e for e in board if e.username == "alice")
    assert alice.score == 58  # best, not the 42 or the wrap-mode 99

    assert len(db_store.leaderboard(GameMode.walls, limit=2)) == 2


def test_leaderboard_filters_by_mode(db_store):
    db_store.add_score("usr_a", "alice", GameMode.wrap, 64)
    assert db_store.leaderboard(GameMode.walls) == []
    assert len(db_store.leaderboard(GameMode.wrap)) == 1


# ---- active games -------------------------------------------------------


def test_publish_upsert_and_get(db_store):
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 5)
    game = db_store.get_active_game("usr_a")
    assert game.userId == "usr_a"
    assert game.score == 5
    assert game.state.snake[0] == (1, 1)

    # Publishing again upserts (one row per user) and updates the score.
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 11)
    assert db_store.get_active_game("usr_a").score == 11
    assert len(db_store.list_active_games()) == 1


def test_list_active_games_sorted_desc(db_store):
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 5)
    db_store.publish_game("usr_b", "bob", _state(), GameMode.walls, 20)
    db_store.publish_game("usr_c", "carol", _state(), GameMode.wrap, 12)
    scores = [g.score for g in db_store.list_active_games()]
    assert scores == [20, 12, 5]


def test_end_game_removes_and_is_idempotent(db_store):
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 5)
    db_store.end_game("usr_a")
    assert db_store.get_active_game("usr_a") is None
    # Second delete is a no-op (no error).
    db_store.end_game("usr_a")


def test_prune_removes_stale_unpinned_games(db_store):
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 5)
    # Backdate the game past the stale window.
    with db_store._session() as session:
        row = session.get(ActiveGameTable, "usr_a")
        row.updated_at = now_ms() - STALE_MS - 1_000
        session.commit()

    assert db_store.prune() is True
    assert db_store.get_active_game("usr_a") is None
    # Nothing left to prune.
    assert db_store.prune() is False


def test_prune_keeps_pinned_games(db_store):
    db_store.publish_game("usr_a", "alice", _state(), GameMode.wrap, 5)
    with db_store._session() as session:
        row = session.get(ActiveGameTable, "usr_a")
        row.pinned = True
        row.updated_at = now_ms() - STALE_MS - 1_000
        session.commit()

    assert db_store.prune() is False
    assert db_store.get_active_game("usr_a") is not None


# ---- lifecycle ----------------------------------------------------------


def test_seed_is_noop_and_reset_is_non_destructive(db_store):
    db_store.create_user("alice", "password1", user_id="usr_a")
    db_store.seed()  # no demo data inserted
    assert db_store.get_user_by_username("alice") is not None
    assert db_store.leaderboard(GameMode.walls) == []
    assert db_store.list_active_games() == []

    db_store.reset()  # ensures schema only; keeps existing rows
    assert db_store.get_user("usr_a") is not None


def test_data_persists_across_store_instances(tmp_path):
    url = f"sqlite:///{tmp_path / 'integration.db'}"
    first = DbStore(url)
    first.create_user("alice", "password1", user_id="usr_a")
    first.add_score("usr_a", "alice", GameMode.walls, 42)
    first.engine.dispose()

    # A brand-new store against the same file sees the persisted data.
    second = DbStore(url)
    assert second.get_user_by_username("alice").id == "usr_a"
    assert second.leaderboard(GameMode.walls)[0].score == 42
    second.engine.dispose()
