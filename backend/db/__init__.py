"""backend.db - database layer for ECDAT / PS 26164 (Ronak / DATABASE lane).

Public surface the FastAPI backend imports:

    from backend.db.database import get_session, init_db, get_engine
    from backend.db import crud
    from backend.db.models import Repository, Scan, Finding

Routes never write raw SQL -- they call `crud` so query logic stays in one
reviewed place. The Postgres engine is built lazily, so importing this package
does not require the Postgres driver to be installed.
"""

from backend.db import crud, database, models
from backend.db.database import get_engine, get_session, init_db

__all__ = [
    "crud",
    "models",
    "database",
    "get_engine",
    "get_session",
    "init_db",
]
