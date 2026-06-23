# Snake Pass Watch — Backend

FastAPI implementation of [`../openapi.yaml`](../openapi.yaml). In-memory store
(no database yet), seeded with fake users, scores, and active games so the
frontend has something to show.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

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
  store.py           # in-memory store + seed data
  auth.py            # auth dependencies (cookie + bearer)
  broker.py          # in-process pub/sub for SSE
  routers/
    auth.py          # /auth/signup, /login, /logout, /me
    scores.py        # /scores  (leaderboard + submit)
    active_games.py  # /active-games  (+ SSE streams)
tests/
```
