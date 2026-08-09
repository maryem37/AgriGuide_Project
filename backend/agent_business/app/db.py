"""PostgreSQL pool for the Business service."""
from contextlib import contextmanager
import os
from typing import Iterator

import psycopg2.extras
from psycopg2 import pool as pg_pool


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://agriadvisor:changeme@localhost:5434/agriadvisor"
)
_pool: pg_pool.SimpleConnectionPool | None = None


def _get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
    return _pool


@contextmanager
def get_cursor() -> Iterator[psycopg2.extras.RealDictCursor]:
    pool = _get_pool()
    connection = pool.getconn()
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        pool.putconn(connection)
