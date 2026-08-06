"""
Pool de connexions PostgreSQL (psycopg2), partagé par tout le service.

Même approche que `backend/auth/app/db.py` : pas d'ORM (requêtes explicites,
faciles à faire correspondre à `database/schema.sql`), pool simple partagé.
"""

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2 import pool as pg_pool

# Contrairement à `auth`, cet agent charge déjà ses secrets (MISTRAL_API_KEY...)
# depuis un `.env` local via pydantic-settings ; on charge aussi ce fichier ici
# pour que DATABASE_URL (voir .env.example) soit pris en compte en local.
load_dotenv()

DATABASE_URL = os.environ.get(
    # Port hôte 5434 par défaut : c'est celui exposé par `docker-compose up -d db`
    # (voir docker-compose.yml — 5432 est souvent déjà pris par un Postgres natif).
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
