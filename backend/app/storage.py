"""Active store selection.

The rest of the app imports ``store`` from here rather than binding a concrete
backend directly. The backend is chosen once, at import time, from the
``DATABASE_URL`` environment variable:

* ``DATABASE_URL`` set   -> :class:`app.db_store.DbStore` (persistent; SQLite by
  default, but any SQLAlchemy URL works — Postgres, MySQL, ...).
* ``DATABASE_URL`` unset -> the in-memory :data:`app.store.store` singleton,
  seeded with demo data. This is what the test suite runs against.

Both backends expose an identical method surface, so routers and the app
lifespan are agnostic to which one is active.
"""

import os

from .db_store import DbStore
from .store import UserRecord
from .store import store as _memory_store

DATABASE_URL = os.environ.get("DATABASE_URL")

store = DbStore(DATABASE_URL) if DATABASE_URL else _memory_store

__all__ = ["store", "UserRecord", "DATABASE_URL"]
