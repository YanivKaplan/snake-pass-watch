"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store


@pytest.fixture()
def client():
    # Entering the TestClient context runs the app lifespan, which resets and
    # reseeds the store — so every test starts from the same fresh state.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded():
    """Reset and reseed the store directly, without spinning up a TestClient.
    Used by tests that drive internal functions (e.g. the SSE generator)."""
    store.reset()
    store.seed()
    yield store


@pytest.fixture()
def auth_token(client):
    """Sign up a fresh user and return (token, user_dict). Cookies are cleared so
    tests can exercise bearer-token auth in isolation."""
    resp = client.post("/api/auth/signup", json={"username": "tester", "password": "secret"})
    assert resp.status_code == 201
    body = resp.json()
    client.cookies.clear()
    return body["token"], body


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Re-export so tests can `from conftest import bearer` if they prefer.
__all__ = ["client", "auth_token", "bearer", "store"]
