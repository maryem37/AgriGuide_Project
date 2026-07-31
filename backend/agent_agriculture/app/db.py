"""
Pool de connexions PostgreSQL (psycopg2), partagé par tout le service.

Même pattern que `backend/auth/app/db.py` : pas d'ORM, requêtes explicites
faciles à faire correspondre à `database/schema.sql`.
"""

from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool

from app.config import settings

_pool: pg_pool.SimpleConnectionPool | None = None


def _get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.SimpleConnectionPool(1, 10, dsn=settings.database_url)
    return _pool


@contextmanager
def get_cursor() -> Iterator[psycopg2.extras.RealDictCursor]:
    """Fournit un curseur RealDict (lignes -> dict) sur une connexion du pool,
    avec commit/rollback automatique."""
    conn = _get_pool().getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)
