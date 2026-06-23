# syntax=docker/dockerfile:1

# --- Backend deps: resolve the locked virtualenv with uv -------------------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Use the image's system Python so the resulting .venv interpreter path is
# valid in the final stage (same base image), instead of a uv-managed download.
ENV UV_PYTHON_PREFERENCE=only-system
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# --- Frontend: build the static SPA (TanStack Start spa mode) --------------
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend .
RUN npm run build

# --- Runtime: Python backend serving the built frontend --------------------
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend/app ./app
# SPA shell + assets land in /app/static, which app.main serves (see STATIC_DIR).
COPY --from=frontend-builder /frontend/dist/client ./static
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
