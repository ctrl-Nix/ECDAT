"""Engine, session factory, and the FastAPI session dependency.

The backend wires routes to the DB like this:

    from fastapi import Depends
    from sqlalchemy.orm import Session
    from backend.db.database import get_session
    from backend.db import crud

    @app.get("/scans/{scan_id}")
    def read_scan(scan_id: int, db: Session = Depends(get_session)):
        return crud.get_scan_with_findings(db, scan_id)

Connection string comes from DATABASE_URL. Default targets the Postgres
container in docker-compose.yml. Tests pass an in-memory SQLite URL, so the
whole layer is verifiable without Docker. The engine is created lazily, so
importing this package never requires the Postgres driver.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

from api.core.config import settings


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    """SQLite ships with FK enforcement off; turn it on so ON DELETE CASCADE
    behaves like Postgres in the offline test-suite. No-op on Postgres."""
    import sqlite3

    if isinstance(dbapi_connection, sqlite3.Connection):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def get_database_url() -> str:
    return settings.DATABASE_URL



def _make_engine(url: str) -> Engine:
    connect_args: dict = {}
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        kwargs["pool_pre_ping"] = True
        if "postgresql" in url and "sslmode=" not in url:
            url += "?" if "?" not in url else "&"
            url += "sslmode=require"
    return create_engine(url, connect_args=connect_args, **kwargs)


_engine: Engine | None = None
_SessionLocal: "sessionmaker[Session] | None" = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _make_engine(get_database_url())
    return _engine


def get_sessionmaker() -> "sessionmaker[Session]":
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _SessionLocal


_db_initialized = False


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    global _db_initialized
    engine = get_engine()
    if not _db_initialized and str(engine.url).startswith("sqlite"):
        try:
            init_db(engine)
        except Exception:
            pass
        _db_initialized = True

    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()



def init_db(target_engine: Engine | None = None) -> None:
    """Create all tables from the ORM metadata.

    In production the tables are created by schema.sql on container init; this
    helper is for tests and a quick local bootstrap against SQLite.
    """
    Base.metadata.create_all(target_engine or get_engine())


def __getattr__(name: str):
    # Lazily expose `engine` / `SessionLocal` without building them at import
    # time (PEP 562).
    if name == "engine":
        return get_engine()
    if name == "SessionLocal":
        return get_sessionmaker()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
