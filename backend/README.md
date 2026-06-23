# Snake Pass Watch — Backend

FastAPI implementation of [`../openapi.yaml`](../openapi.yaml).

## Storage backends

The active store is chosen at startup from the `DATABASE_URL` environment
variable:

- **`DATABASE_URL` set** — a persistent, SQLAlchemy-backed store. The schema is
  database-agnostic (portable column types only), so any SQLAlchemy URL works.
  SQLite is the default target; Postgres et al. can be added later by changing
  only the URL. No seed data is inserted.
- **`DATABASE_URL` unset** — the in-memory store, seeded with demo users,
  scores, and active games (see below). State resets on every restart. The test
  suite runs against this backend.

## Run

```bash
uv sync
# Persistent SQLite (creates ./snake.db):
DATABASE_URL=sqlite:///./snake.db uv run uvicorn app.main:app --reload
# ...or omit DATABASE_URL to run the in-memory seeded store.
```

`make backend` runs against SQLite by default (override with
`make backend DATABASE_URL=...`).

The API is served under `/api` (e.g. `http://127.0.0.1:8000/api/active-games`).
Interactive docs: `http://127.0.0.1:8000/docs`.

## Test

```bash
uv run pytest
```

## Auth

Sessions use a token that is both:

- set as the HttpOnly `session` cookie (what the browser frontend sends
  automatically), and
- returned in the login/signup response body and accepted as
  `Authorization: Bearer <token>` (handy for non-browser clients).

Passwords are hashed with salted PBKDF2-HMAC-SHA256 (stdlib only).

### Seeded users

| username | password    |
| -------- | ----------- |
| alice    | password1   |
| bob      | password2   |
| carol    | hunter22    |
| dave     | snakey99    |

`alice` (walls) and `carol` (wrap) have seeded active games that stay visible
indefinitely; games published by other users are pruned ~30s after their last
update.

## Layout

```
app/
  main.py            # app wiring: lifespan (seed + prune), CORS, error handlers
  models.py          # Pydantic models mirroring openapi.yaml schemas
  security.py        # password hashing + token generation
  store.py           # in-memory store + seed data (default / tests)
  db.py              # SQLAlchemy schema + engine factory (database-agnostic)
  db_store.py        # persistent store backed by SQLAlchemy
  storage.py         # selects the active backend from DATABASE_URL
  auth.py            # auth dependencies (cookie + bearer)
  broker.py          # in-process pub/sub for SSE
  routers/
    auth.py          # /auth/signup, /login, /logout, /me
    scores.py        # /scores  (leaderboard + submit)
    active_games.py  # /active-games  (+ SSE streams)
tests/               # unit/API tests (in-memory backend)
  integration/       # DB integration tests (run with `make backend-it`)
```
