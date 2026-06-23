.PHONY: install backend frontend backend-tests backend-it frontend-tests test

install:
	cd backend && uv sync
	cd frontend && npm install

backend:
	cd backend && uv run uvicorn app.main:app --env-file .env --reload

frontend:
	cd frontend && npm run dev

backend-tests:
	cd backend && uv run pytest tests

# Database integration tests. Run against a temporary on-disk SQLite database
# (set up by tests_integration/conftest.py) so the app selects the SQLAlchemy
# backend (DbStore) and exercises full flows end to end.
backend-it:
	cd backend && uv run pytest tests_integration

frontend-tests:
	cd frontend && npm run test

test: backend-tests backend-it frontend-tests
