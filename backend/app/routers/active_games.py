"""Live game state for spectators, plus realtime SSE streams."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..broker import broker
from ..models import ActiveGame, Error, PublishGameRequest
from ..store import UserRecord, store

router = APIRouter(prefix="/active-games", tags=["active-games"])

# Send a comment line this often (seconds) while idle to keep the SSE
# connection and any intermediary proxies from timing out.
_KEEPALIVE_SECONDS = 15


def _sse(payload: object) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _games_payload() -> list[dict]:
    return [game.model_dump(mode="json") for game in store.list_active_games()]


def _game_payload(user_id: str) -> Optional[dict]:
    game = store.get_active_game(user_id)
    return game.model_dump(mode="json") if game else None


async def _event_stream(request: Request, snapshot):
    """Yield an initial snapshot, then a fresh one on every broker notification."""
    queue = broker.subscribe()
    try:
        yield _sse(snapshot())
        while True:
            if await request.is_disconnected():
                break
            try:
                await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield _sse(snapshot())
    finally:
        broker.unsubscribe(queue)


@router.get("", response_model=list[ActiveGame], summary="List active games")
def list_active_games() -> list[ActiveGame]:
    return store.list_active_games()


@router.get("/stream", summary="Subscribe to the active-games list (SSE)")
async def stream_active_games(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request, _games_payload),
        media_type="text/event-stream",
    )


@router.put(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": Error}},
    summary="Publish (upsert) the authenticated user's live game state",
)
def publish_game_state(
    body: PublishGameRequest,
    user: UserRecord = Depends(get_current_user),
) -> Response:
    store.publish_game(user.id, user.username, body.state, body.mode, body.score)
    broker.notify()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": Error}},
    summary="End the authenticated user's active game",
)
def end_game(user: UserRecord = Depends(get_current_user)) -> Response:
    store.end_game(user.id)
    broker.notify()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{user_id}",
    response_model=Optional[ActiveGame],
    summary="Get a single user's active game",
)
def get_active_game(user_id: str) -> Optional[ActiveGame]:
    return store.get_active_game(user_id)


@router.get(
    "/{user_id}/stream",
    summary="Subscribe to a single user's active game (SSE)",
)
async def stream_active_game(request: Request, user_id: str) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request, lambda: _game_payload(user_id)),
        media_type="text/event-stream",
    )
