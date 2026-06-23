"""Authentication dependencies.

A session token is accepted either as the HttpOnly ``session`` cookie (what the
browser frontend sends) or as an ``Authorization: Bearer <token>`` header (handy
for non-browser API clients). The header takes precedence when both are present.
"""

from typing import Optional

from fastapi import HTTPException, Request, Response, status

from .store import UserRecord, store

SESSION_COOKIE = "session"


def extract_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header[len("bearer ") :].strip()
    return request.cookies.get(SESSION_COOKIE)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def get_optional_user(request: Request) -> Optional[UserRecord]:
    """Resolve the current user, or ``None`` if unauthenticated. Never raises."""
    token = extract_token(request)
    if not token:
        return None
    return store.user_for_token(token)


def get_current_user(request: Request) -> UserRecord:
    """Resolve the current user or raise 401."""
    user = get_optional_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user
