"""Integration-test harness backed by a temporary on-disk SQLite database.

``DATABASE_URL`` must be set *before* the app is imported, because the store
selector (:mod:`app.storage`) reads it at import time. So this conftest points
it at a throwaway SQLite file first, then imports the app — guaranteeing these
tests exercise the real :class:`~app.db_store.DbStore` backend (and the same
on-disk persistence path the server uses), never the in-memory store.

The temp database lives in a per-session temp directory that is removed on
teardown; each test additionally starts from a freshly recreated schema.
"""

import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

# --- configure the backend BEFORE importing the app -----------------------
_TMP_DIR = tempfile.mkdtemp(prefix="snake_it_")
_DB_PATH = os.path.join(_TMP_DIR, "integration.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from app.db import Base  # noqa: E402  (must follow the env setup above)
from app.db_store import DbStore  # noqa: E402
from app.main import app  # noqa: E402
from app.storage import store  # noqa: E402

assert isinstance(store, DbStore), "integration tests must run against the DB backend"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_tmp_database():
    """Dispose the engine and delete the temp database when the session ends."""
    yield
    store.engine.dispose()
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Give every test a clean schema so flows don't leak into each other."""
    Base.metadata.drop_all(store.engine)
    Base.metadata.create_all(store.engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_store():
    """A separate, isolated in-memory ``DbStore`` for direct (non-API) tests."""
    store_instance = DbStore("sqlite://")
    yield store_instance
    store_instance.engine.dispose()
