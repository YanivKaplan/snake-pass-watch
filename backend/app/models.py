"""Pydantic models mirroring the schemas in openapi.yaml.

These types are the single source of truth for request/response shapes and are
shared between the routers and the in-memory store.
"""

from enum import Enum

from pydantic import BaseModel, Field

# A grid coordinate as an [x, y] (column, row) tuple. Pydantic accepts a 2-element
# JSON array and serializes it back to one.
Cell = tuple[int, int]


class GameMode(str, Enum):
    """Snake game mode — walls (deadly edges) or wrap (toroidal edges)."""

    walls = "walls"
    wrap = "wrap"


class Direction(str, Enum):
    up = "up"
    down = "down"
    left = "left"
    right = "right"


class User(BaseModel):
    id: str
    username: str


class AuthResponse(User):
    """A `User` plus the session token.

    The token is also delivered as the HttpOnly `session` cookie (which the
    browser frontend relies on). It is included in the body as well so that
    non-browser clients can use it as a `Authorization: Bearer <token>` header.
    """

    token: str


class Credentials(BaseModel):
    username: str
    password: str


class GameState(BaseModel):
    """Serialized, compact snapshot of a snake game."""

    width: int = Field(ge=1)
    height: int = Field(ge=1)
    snake: list[Cell] = Field(description="Snake body cells, head first.")
    food: Cell
    dir: Direction
    alive: bool


class ScoreEntry(BaseModel):
    id: str
    userId: str
    username: str
    mode: GameMode
    score: int = Field(ge=0)
    createdAt: int = Field(description="Creation time as a Unix epoch timestamp in ms.")


class ActiveGame(BaseModel):
    userId: str
    username: str
    mode: GameMode
    score: int = Field(ge=0)
    state: GameState
    updatedAt: int = Field(description="Last-update time as a Unix epoch timestamp in ms.")


class SubmitScoreRequest(BaseModel):
    mode: GameMode
    score: int = Field(ge=0)


class PublishGameRequest(BaseModel):
    state: GameState
    mode: GameMode
    score: int = Field(ge=0)


class Error(BaseModel):
    error: str = Field(description="Human-readable error message.")
