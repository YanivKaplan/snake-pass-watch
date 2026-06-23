"""Fixtures for the database integration tests.

Two kinds of tests live here:

* Direct ``DbStore`` tests, which construct their own isolated in-memory store
  (the ``db_store`` fixture) and need no environment configuration.
* API-level tests, which drive the real FastAPI app and therefore require the
  app to have been wired to a database backend via ``DATABASE_URL``. The
  ``client`` fixture skips those tests if no DB backend is active, so they can
  never silently pass against the in-memory store. Run them via
  ``make backend-it`` (which sets ``DATABASE_URL``).
"""

import pytest
from fastapi.testclient import TestClient

from app.db import Base
from app.db_store import DbStore
from app.main import app
from app.storage import store


@pytest.fixture()
def db_store():
    """A fresh, isolated in-memory ``DbStore`` for direct (non-API) tests."""
    store_instance = DbStore("sqlite://")
    yield store_instance
    store_instance.engine.dispose()


@pytest.fixture()
def client():
    """API client backed by the configured database store.

    Skips unless the app actually selected a DB backend, so these tests are only
    meaningful when ``DATABASE_URL`` points at a database.
    """
    if not isinstance(store, DbStore):
        pytest.skip("DATABASE_URL is not set to a database backend")
    # Start each test from a clean schema.
    Base.metadata.drop_all(store.engine)
    Base.metadata.create_all(store.engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    """Sign up a fresh user; return (bearer headers, user dict)."""
    resp = client.post(
        "/api/auth/signup", json={"username": "itester", "password": "secret"}
    )
    assert resp.status_code == 201
    body = resp.json()
    client.cookies.clear()
    return {"Authorization": f"Bearer {body['token']}"}, body
