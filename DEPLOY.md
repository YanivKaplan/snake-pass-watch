# Deploying to Render (free tier)

Render deploys **only the app** — a single Docker web service (FastAPI backend
serving the built SPA). The database is an **external managed Postgres (Aiven)**,
connected via the `DATABASE_URL` environment variable. No Render-managed Postgres
is created. The `Dockerfile` and app code are unchanged; all wiring is env vars
(see [`render.yaml`](./render.yaml)).

## One-time deploy

1. Push this branch to GitHub (the repo Render reads from).
2. Render Dashboard → **New** → **Blueprint** → select this repository. Render
   reads `render.yaml` and shows the free web service `snake-pass-watch`.
3. Set the `DATABASE_URL` value (marked `sync:false`, so Render prompts for it).
   Build it from the Aiven service details using the **psycopg v3 scheme** and
   Aiven's **required SSL**:

   ```
   postgresql+psycopg://<user>:<password>@<host>:<port>/<database>?sslmode=require
   ```

   The values come from the Aiven service page (Host / Port / User / Password /
   Database name). Note the scheme is `postgresql+psycopg://` (psycopg v3), not
   the `postgres://` Aiven shows in its Service URI.
4. Leave `PORT` as `8000`.
5. **Apply.** The app auto-creates its schema on first boot
   (`Base.metadata.create_all`) — no migration step. It is served at
   `https://snake-pass-watch.onrender.com` (health check: `/api/health`).

## Why the scheme and SSL matter

- The backend uses **psycopg v3**. SQLAlchemy maps a bare `postgresql://` URL to
  the psycopg2 dialect (not installed) and would crash on boot;
  `postgresql+psycopg://` selects psycopg v3 explicitly.
- Aiven requires TLS, so keep **`?sslmode=require`** in the URL.

## Secrets

`DATABASE_URL` carries the database password and is **never committed** — it
lives only as a Render env var (`sync:false` in `render.yaml`). If the password
is exposed, rotate it in Aiven and update the env var.

## Free-tier caveat

The Render web service **sleeps after ~15 min of inactivity** and cold-starts on
the next request (tens of seconds). Open SSE connections (`/api/active-games`)
drop across a sleep/cold-start cycle. The external Aiven database is unaffected.
