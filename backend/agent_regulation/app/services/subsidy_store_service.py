"""Accès aux données de la table `subsidies` — requêtes SQL explicites sur
`database/schema.sql` (même approche que `backend/auth/app/services/user_service.py`,
pas d'ORM).
"""

from app.db import get_cursor
from app.schemas.subsidy import SubsidyUpsertInput

# Colonnes mises à jour lors d'un upsert (hors last_verified_at/updated_at,
# gérées séparément dans la requête).
_UPSERT_COLUMNS = (
    "name",
    "description",
    "eligibility",
    "amount",
    "region",
    "start_date",
    "end_date",
    "application_procedure",
    "source_name",
    "is_official",
)


def upsert_subsidy(data: SubsidyUpsertInput) -> dict:
    """Crée l'aide si `source_url` est inconnue, sinon met à jour ses champs.

    `last_verified_at` est toujours rafraîchi. `updated_at` n'est modifié que
    si au moins un champ a réellement changé (comparaison faite côté SQL).
    Retourne la ligne stockée, avec une clé `was_created` (bool) en plus.
    """
    set_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in _UPSERT_COLUMNS)
    changed_old = ", ".join(f"subsidies.{col}" for col in _UPSERT_COLUMNS)
    changed_new = ", ".join(f"EXCLUDED.{col}" for col in _UPSERT_COLUMNS)

    with get_cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO subsidies (
                name, description, eligibility, amount, region,
                start_date, end_date, application_procedure,
                source_name, source_url, is_official, last_verified_at
            ) VALUES (
                %(name)s, %(description)s, %(eligibility)s, %(amount)s, %(region)s,
                %(start_date)s, %(end_date)s, %(application_procedure)s,
                %(source_name)s, %(source_url)s, %(is_official)s, now()
            )
            ON CONFLICT (source_url) DO UPDATE SET
                {set_clause},
                last_verified_at = now(),
                updated_at = CASE
                    WHEN ({changed_old}) IS DISTINCT FROM ({changed_new})
                    THEN now()
                    ELSE subsidies.updated_at
                END
            RETURNING *, (xmax = 0) AS was_created
            """,
            data.model_dump(),
        )
        row = cur.fetchone()
        return _row_to_dict(row)


def list_active_subsidies(limit: int = 4) -> list[dict]:
    """Aides actives (sans échéance ou échéance future), triées par échéance
    la plus proche en premier."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM subsidies
            WHERE end_date IS NULL OR end_date >= CURRENT_DATE
            ORDER BY end_date ASC NULLS LAST, name ASC
            LIMIT %s
            """,
            (limit,),
        )
        return [_row_to_dict(row) for row in cur.fetchall()]


def _row_to_dict(row: dict) -> dict:
    return {**row, "id": str(row["id"])}
