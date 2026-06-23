"""FastAPI application entrypoint.

Run locally with:  uv run uvicorn app.main:app --reload
The API is mounted under ``/api`` to match the OpenAPI ``servers`` entry.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .broker import broker
from .routers import active_games, auth, scores
from .storage import store

_PRUNE_INTERVAL_SECONDS = 10

# Built frontend (TanStack Start SPA shell + assets). In the Docker image these
# live at /app/static; in local dev the directory is absent and serving is
# skipped (the frontend runs on its own Vite dev server instead).
STATIC_DIR = Path(
    os.environ.get("STATIC_DIR", Path(__file__).resolve().parent.parent / "static")
)


async def _prune_loop() -> None:
    """Periodically drop stale active games and notify SSE subscribers."""
    while True:
        await asyncio.sleep(_PRUNE_INTERVAL_SECONDS)
        if store.prune():
            broker.notify()


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.reset()
    store.seed()
    task = asyncio.create_task(_prune_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Snake Pass Watch — Backend API",
    version="1.0.0",
    description="REST + SSE backend implementing openapi.yaml.",
    lifespan=lifespan,
)

# Allow the Vite dev frontend (any localhost port) to call the API with cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    # Map FastAPI's default {"detail": ...} onto the spec's {"error": ...} shape.
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "Invalid request"
    return JSONResponse(status_code=400, content={"error": message})


@app.get("/api/health", tags=["meta"], summary="Liveness check")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(scores.router, prefix="/api")
app.include_router(active_games.router, prefix="/api")


# Serve the built single-page frontend, if present. Registered last so the /api
# routes above always take precedence. Real asset files are served directly;
# everything else falls back to the SPA shell so client-side routing works.
_SPA_SHELL = STATIC_DIR / "_shell.html"

if _SPA_SHELL.is_file():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        # API routes are matched before this catch-all; guard so unknown /api
        # paths still 404 as JSON rather than returning the HTML shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_SPA_SHELL)
