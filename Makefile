.PHONY: install backend frontend backend-tests frontend-tests test

install:
	cd backend && uv sync
	cd frontend && bun install

backend:
	cd backend && uv run uvicorn app.main:app --reload

frontend:
	cd frontend && bun run dev

backend-tests:
	cd backend && uv run pytest

frontend-tests:
	cd frontend && bun run test

test: backend-tests frontend-tests
