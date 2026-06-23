"""Score submission and leaderboards."""

from fastapi import APIRouter, Depends, Query, status

from ..auth import get_current_user
from ..models import Error, GameMode, ScoreEntry, SubmitScoreRequest
from ..storage import UserRecord, store

router = APIRouter(tags=["scores"])


@router.get(
    "/scores",
    response_model=list[ScoreEntry],
    summary="Get the leaderboard for a mode",
)
def get_leaderboard(
    mode: GameMode = Query(description="Game mode to rank."),
    limit: int = Query(default=10, ge=1, description="Maximum number of entries."),
) -> list[ScoreEntry]:
    return store.leaderboard(mode, limit)


@router.post(
    "/scores",
    status_code=status.HTTP_201_CREATED,
    response_model=ScoreEntry,
    responses={401: {"model": Error}},
    summary="Submit a score",
)
def submit_score(
    body: SubmitScoreRequest,
    user: UserRecord = Depends(get_current_user),
) -> ScoreEntry:
    return store.add_score(user.id, user.username, body.mode, body.score)
