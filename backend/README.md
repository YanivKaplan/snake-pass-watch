# Snake Pass Watch — Backend

FastAPI implementation of [`../openapi.yaml`](../openapi.yaml).

## Docker (full app: backend + built frontend)

The repo-root `Dockerfile` builds the frontend (TanStack Start SPA mode) and
bakes the static output into a Python image that serves both the SPA and the
`/api`. The store is **configured from outside the image** via `DATABASE_URL`
(never baked in, no seed data), so SQLite can be swapped for Postgres without a
rebuild.

```bash
docker compose up --build      # serves http://localhost:8000
```

`docker-compose.yml` runs a bundled **Postgres** `db` service and points the
app at it by default (`postgresql+psycopg://…@db:5432/snake`). Config is read
from the repo-root `.env` (copy `.env.example` to `.env` first); Postgres data
persists in the `pgdata` volume, independent of the app container's lifecycle.

To use SQLite instead — handy for a quick throwaway run — override `DATABASE_URL`
to a file under the host-mounted `./data` volume:

```bash
DATABASE_URL=sqlite:////data/snake.db docker compose up --build
```

The store layer is database-agnostic, so only the URL changes. Plain
`docker run` works too (no compose, no Postgres service):

```bash
docker run -p 8000:8000 -e DATABASE_URL=sqlite:////data/snake.db -v "$PWD/data:/data" snake-pass-watch:local
```

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
cp .env.example .env   # sets DATABASE_URL=sqlite:///./snake.db
make backend           # uvicorn --env-file .env
```

`.env` is git-ignored; `.env.example` holds the default. `make backend` loads
`DATABASE_URL` from `.env` via uvicorn's `--env-file`. Edit `.env` to point at
another database (any SQLAlchemy URL), or comment the line out for the in-memory
seeded store. Running uvicorn yourself works too:

```bash
DATABASE_URL=sqlite:///./snake.db uv run uvicorn app.main:app --reload
```

The API is served under `/api` (e.g. `http://127.0.0.1:8000/api/active-games`).
Interactive docs: `http://127.0.0.1:8000/docs`.

## Test

```bash
make backend-tests   # unit/API tests (in-memory store)
make backend-it      # DB integration tests (temporary SQLite database)
# or directly:
uv run pytest               # unit/API tests (testpaths = tests/)
uv run pytest tests_integration
```

`tests_integration/` runs the full flows (sign up, log in, submit a score, read
the leaderboard) end to end against a throwaway on-disk SQLite database, so it
exercises the real SQLAlchemy backend rather than the in-memory store.

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
tests_integration/   # DB integration tests, temp SQLite (`make backend-it`)
```
