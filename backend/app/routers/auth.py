"""Auth endpoints: signup, login, logout, current-session lookup."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..auth import (
    clear_session_cookie,
    extract_token,
    get_optional_user,
    set_session_cookie,
)
from ..models import AuthResponse, Credentials, Error, User
from ..security import verify_password
from ..storage import UserRecord, store

router = APIRouter(prefix="/auth", tags=["auth"])

# Validation rules ported from the frontend mock.
MIN_USERNAME_LEN = 2
MIN_PASSWORD_LEN = 4


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    responses={400: {"model": Error}, 409: {"model": Error}},
    summary="Create a new account and start a session",
)
def signup(creds: Credentials, response: Response) -> AuthResponse:
    username = creds.username.strip()
    if len(username) < MIN_USERNAME_LEN:
        raise HTTPException(400, "Username must be at least 2 characters")
    if len(creds.password) < MIN_PASSWORD_LEN:
        raise HTTPException(400, "Password must be at least 4 characters")
    if store.get_user_by_username(username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user = store.create_user(username, creds.password)
    token = store.issue_token(user.id)
    set_session_cookie(response, token)
    return AuthResponse(id=user.id, username=user.username, token=token)


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={401: {"model": Error}},
    summary="Authenticate and start a session",
)
def login(creds: Credentials, response: Response) -> AuthResponse:
    user = store.get_user_by_username(creds.username.strip())
    if user is None or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = store.issue_token(user.id)
    set_session_cookie(response, token)
    return AuthResponse(id=user.id, username=user.username, token=token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the current session",
)
def logout(request: Request) -> Response:
    token = extract_token(request)
    if token:
        store.revoke_token(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get(
    "/me",
    response_model=Optional[User],
    summary="Get the currently authenticated user",
)
def current_user(user: Optional[UserRecord] = Depends(get_optional_user)) -> Optional[User]:
    # Returns 200 with `null` when logged out, so the client can tell "logged
    # out" apart from a transport failure.
    if user is None:
        return None
    return User(id=user.id, username=user.username)
