"""Tests du service de stockage des aides financières (table `subsidies`).

Nécessite une vraie base PostgreSQL démarrée avec `database/schema.sql`
appliqué (voir `docker-compose up -d db`, ou README de `backend/auth`).
Ignorés automatiquement si la base n'est pas joignable.
"""

import uuid
from datetime import date, timedelta

import psycopg2
import pytest

from app.db import DATABASE_URL
from app.schemas.subsidy import SubsidyUpsertInput
from app.services import subsidy_store_service


def _db_available() -> bool:
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="Base PostgreSQL non joignable (DATABASE_URL)."
)


def _sample_input(source_url: str, **overrides) -> SubsidyUpsertInput:
    base = dict(
        name="Aide de test",
        description="Description de test.",
        eligibility="Exploitants agricoles",
        amount="1000 €",
        region="Occitanie",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=180),
        application_procedure="Dossier en ligne",
        source_name="test.gouv.fr",
        source_url=source_url,
        is_official=True,
    )
    base.update(overrides)
    return SubsidyUpsertInput(**base)


def test_upsert_creates_new_subsidy():
    url = f"https://test.example/{uuid.uuid4().hex}"
    result = subsidy_store_service.upsert_subsidy(_sample_input(url))
    assert result["was_created"] is True
    assert result["name"] == "Aide de test"
    assert result["source_url"] == url


def test_upsert_updates_existing_subsidy_instead_of_duplicating():
    url = f"https://test.example/{uuid.uuid4().hex}"
    first = subsidy_store_service.upsert_subsidy(_sample_input(url))
    second = subsidy_store_service.upsert_subsidy(_sample_input(url, amount="2000 €"))

    assert second["was_created"] is False
    assert second["id"] == first["id"]
    assert second["amount"] == "2000 €"

    rows = subsidy_store_service.list_active_subsidies(limit=1000)
    matching = [r for r in rows if r["source_url"] == url]
    assert len(matching) == 1


def test_list_active_subsidies_sorted_by_end_date():
    near_url = f"https://test.example/{uuid.uuid4().hex}"
    far_url = f"https://test.example/{uuid.uuid4().hex}"
    subsidy_store_service.upsert_subsidy(
        _sample_input(far_url, end_date=date.today() + timedelta(days=60))
    )
    subsidy_store_service.upsert_subsidy(
        _sample_input(near_url, end_date=date.today() + timedelta(days=5))
    )

    rows = subsidy_store_service.list_active_subsidies(limit=1000)
    ordered_urls = [r["source_url"] for r in rows if r["source_url"] in (near_url, far_url)]
    assert ordered_urls == [near_url, far_url]


def test_list_active_subsidies_excludes_expired():
    expired_url = f"https://test.example/{uuid.uuid4().hex}"
    subsidy_store_service.upsert_subsidy(
        _sample_input(expired_url, end_date=date.today() - timedelta(days=1))
    )

    rows = subsidy_store_service.list_active_subsidies(limit=1000)
    assert all(r["source_url"] != expired_url for r in rows)


def test_list_active_subsidies_respects_limit():
    for _ in range(3):
        subsidy_store_service.upsert_subsidy(_sample_input(f"https://test.example/{uuid.uuid4().hex}"))

    rows = subsidy_store_service.list_active_subsidies(limit=2)
    assert len(rows) <= 2


def test_upsert_accepts_long_text_fields():
    """Régression : `description`/`eligibility`/`amount`/`application_procedure`/
    `source_url` doivent accepter des textes de plus de 255 caractères (ils
    sont en TEXT, pas VARCHAR(255)) — cf. montants/URLs longs renvoyés par
    l'extraction LLM du Subsidy Search."""
    long_text = "A" * 500
    long_url = f"https://test.example/{'b' * 400}/{uuid.uuid4().hex}"

    result = subsidy_store_service.upsert_subsidy(
        _sample_input(
            long_url,
            description=long_text,
            eligibility=long_text,
            amount=long_text,
            application_procedure=long_text,
        )
    )

    assert result["was_created"] is True
    assert result["description"] == long_text
    assert result["eligibility"] == long_text
    assert result["amount"] == long_text
    assert result["application_procedure"] == long_text
    assert result["source_url"] == long_url
