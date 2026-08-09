"""Persistence for generated scenarios and confirmed farmer decisions.

PostgreSQL is the production backend. An in-process cache keeps local tests
and disconnected development usable, but it is never described as durable.
Set BUSINESS_PERSISTENCE_REQUIRED=1 to fail requests when PostgreSQL is down.
"""
from __future__ import annotations

import os
from uuid import UUID

from psycopg2.extras import Json

from app.db import get_cursor
from app.models.schemas import BusinessScenario, FarmerDecisionResponse


_scenario_cache: dict[str, BusinessScenario] = {}
_decision_cache: dict[str, FarmerDecisionResponse] = {}


class PersistenceUnavailableError(RuntimeError):
    pass


def _database_enabled() -> bool:
    return os.getenv("BUSINESS_PERSISTENCE_MODE", "database").lower() != "memory"


def database_persistence_enabled() -> bool:
    return _database_enabled()


def _required() -> bool:
    return os.getenv("BUSINESS_PERSISTENCE_REQUIRED", "1").lower() in {"1", "true", "yes"}


def save_scenarios(scenarios: list[BusinessScenario]) -> str:
    for scenario in scenarios:
        if scenario.id:
            _scenario_cache[scenario.id] = scenario
    if not _database_enabled():
        return "memory"

    try:
        with get_cursor() as cursor:
            for scenario in scenarios:
                payload = scenario.model_dump(mode="json")
                cursor.execute(
                    """
                    INSERT INTO business_scenarios
                        (id, terrain_id, budget_input, culture, quantite_par_ha,
                         profit_estime, risque_score, risque_description,
                         solution_risque, matching_score, etude_marche,
                         superficie_max_financable_ha, superficie_conseillee_ha,
                         scenario_payload, created_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        scenario_payload = EXCLUDED.scenario_payload,
                        matching_score = EXCLUDED.matching_score
                    """,
                    (
                        scenario.id,
                        scenario.terrain_id,
                        scenario.budget_input,
                        scenario.culture,
                        scenario.quantite_par_ha,
                        scenario.profit_estime,
                        scenario.risque_score,
                        scenario.risque_description,
                        scenario.solution_risque,
                        scenario.matching_score,
                        Json(scenario.etude_marche),
                        scenario.superficie_max_financable_ha,
                        scenario.superficie_conseillee_ha,
                        Json(payload),
                        scenario.created_at,
                    ),
                )
        return "postgresql"
    except Exception as exc:
        if _required():
            raise PersistenceUnavailableError(
                f"Impossible d'enregistrer les scénarios dans PostgreSQL: {exc}"
            ) from exc
        print(f"[business.persistence] PostgreSQL unavailable, memory fallback: {exc}")
        return "memory"


def get_owned_terrain_area(terrain_id: str, user_id: str) -> float | None:
    """Return the authoritative area only when the terrain belongs to user."""
    areas = get_owned_terrains_total_area([terrain_id], user_id)
    return areas


def get_owned_terrains_total_area(terrain_ids: list[str], user_id: str) -> float | None:
    """Sum superficie_ha for all owned terrains. None if any id is missing/unauthorized."""
    unique_ids = list(dict.fromkeys([tid for tid in terrain_ids if tid]))
    if not unique_ids:
        return None
    if not _database_enabled():
        return None
    try:
        with get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, superficie_ha
                FROM terrains
                WHERE user_id = %s AND id = ANY(%s::uuid[])
                """,
                (user_id, unique_ids),
            )
            rows = cursor.fetchall()
            if len(rows) != len(unique_ids):
                return None
            return float(sum(float(row["superficie_ha"]) for row in rows))
    except Exception as exc:
        if _required():
            raise PersistenceUnavailableError(
                f"Impossible de vérifier les terrains PostgreSQL: {exc}"
            ) from exc
        return None


def get_scenarios(ids: list[str]) -> dict[str, BusinessScenario]:
    result = {scenario_id: _scenario_cache[scenario_id] for scenario_id in ids if scenario_id in _scenario_cache}
    missing = [scenario_id for scenario_id in ids if scenario_id not in result]
    if not missing or not _database_enabled():
        return result

    valid_ids: list[str] = []
    for value in missing:
        try:
            valid_ids.append(str(UUID(value)))
        except ValueError:
            continue
    if not valid_ids:
        return result

    try:
        with get_cursor() as cursor:
            cursor.execute(
                "SELECT scenario_payload FROM business_scenarios WHERE id = ANY(%s::uuid[])",
                (valid_ids,),
            )
            for row in cursor.fetchall():
                scenario = BusinessScenario.model_validate(row["scenario_payload"])
                if scenario.id:
                    result[scenario.id] = scenario
                    _scenario_cache[scenario.id] = scenario
    except Exception as exc:
        if _required():
            raise PersistenceUnavailableError(
                f"Impossible de relire les scénarios PostgreSQL: {exc}"
            ) from exc
    return result


def save_decision(decision: FarmerDecisionResponse) -> str:
    _decision_cache[decision.decision_id] = decision
    if not _database_enabled():
        return "memory"
    try:
        with get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO farmer_decisions
                    (id, terrain_id, statut, cout_final, decision_payload,
                     created_at, confirmed_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                """,
                (
                    decision.decision_id,
                    decision.terrain_id,
                    decision.statut,
                    decision.cout_final,
                    Json(decision.model_dump(mode="json")),
                    decision.created_at,
                ),
            )
            for allocation in decision.allocations:
                cursor.execute(
                    """
                    INSERT INTO decision_allocations
                        (decision_id, scenario_id, culture, hectares_alloues,
                         cout_alloue, date_maturite_prevue)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        decision.decision_id,
                        allocation["scenario_id"],
                        allocation["culture"],
                        allocation["hectares_alloues"],
                        allocation["cout_alloue"],
                        allocation["date_maturite_prevue"],
                    ),
                )
        return "postgresql"
    except Exception as exc:
        if _required():
            raise PersistenceUnavailableError(
                f"Impossible d'enregistrer la décision dans PostgreSQL: {exc}"
            ) from exc
        print(f"[business.persistence] Decision kept in memory only: {exc}")
        return "memory"


def get_latest_decision(terrain_id: str) -> FarmerDecisionResponse | None:
    cached = [
        decision for decision in _decision_cache.values() if decision.terrain_id == terrain_id
    ]
    if cached:
        return max(cached, key=lambda decision: decision.created_at)
    if not _database_enabled():
        return None
    try:
        with get_cursor() as cursor:
            cursor.execute(
                """
                SELECT decision_payload
                FROM farmer_decisions
                WHERE terrain_id = %s AND statut IN ('confirmed', 'monitoring')
                ORDER BY confirmed_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                (terrain_id,),
            )
            row = cursor.fetchone()
            if not row or not row["decision_payload"]:
                return None
            decision = FarmerDecisionResponse.model_validate(row["decision_payload"])
            _decision_cache[decision.decision_id] = decision
            return decision
    except Exception as exc:
        if _required():
            raise PersistenceUnavailableError(
                f"Impossible de relire la décision PostgreSQL: {exc}"
            ) from exc
        return None
