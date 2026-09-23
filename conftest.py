"""Put the repo root on sys.path so `import backend.db...` works under pytest.

Also overrides DATABASE_URL to an in-memory SQLite database before any app
module is imported, so CI tests run inside Docker (where the image user has no
write access to /app) without needing a real database file on disk.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Force in-memory SQLite for all tests so Docker CI never needs a writable
# filesystem. Must be set before `api.database` or `api.core.config` are imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_KEY", "ci-test-key")

from sqlalchemy import event as _sa_event
from sqlalchemy.engine import Engine as _Engine

@_sa_event.listens_for(_Engine, "connect")
def _set_sqlite_fk_pragma(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

