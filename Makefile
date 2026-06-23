.PHONY: install backend frontend backend-tests backend-it frontend-tests test

install:
	cd backend && uv sync
	cd frontend && npm install

backend:
	cd backend && DATABASE_URL=$(DATABASE_URL) uv run uvicorn app.main:app --reload

# DATABASE_URL selects the store backend. Default to a local SQLite file; any
# SQLAlchemy URL works (e.g. postgresql+psycopg://...). Leave unset to run
# against the in-memory seeded store instead.
DATABASE_URL ?= sqlite:///./snake.db

frontend:
	cd frontend && npm run dev

backend-tests:
	cd backend && uv run pytest tests --ignore=tests/integration

# Database integration tests. Runs against an in-memory SQLite DB so the app
# selects the SQLAlchemy backend (DbStore) rather than the in-memory store.
backend-it:
	cd backend && DATABASE_URL=sqlite:// uv run pytest tests/integration

frontend-tests:
	cd frontend && npm run test

test: backend-tests frontend-tests
