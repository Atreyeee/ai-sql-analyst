"""
SQLAlchemy engine and session management.

We use SQLAlchemy Core (not the ORM) for this project. We are not
mapping database rows to Python classes — we're inspecting schema
and executing raw/generated SQL. SQLAlchemy Core gives us connection
pooling, a database-agnostic execution interface, and (importantly)
a rich schema-introspection API, without forcing an ORM model layer
we don't need.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection

from app.database.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Returns a singleton SQLAlchemy engine.

    The engine manages a connection pool internally — we do NOT want
    to create a new engine (and therefore a new pool) on every request.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # detects stale connections before using them
        )
    return _engine


@contextmanager
def get_connection() -> Iterator[Connection]:
    """
    Context manager yielding a live database connection from the pool.

    Ensures the connection is always returned to the pool (via the
    'with' block), even if an exception occurs during query execution.
    """
    engine = get_engine()
    with engine.connect() as conn:
        yield conn