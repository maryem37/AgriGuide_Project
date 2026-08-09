"""Deterministic production-cost and profitability calculations.

Priority order for cost data:
1. A real, operator-provided CSV (``BUSINESS_COST_DATA_CSV``).
2. A bottom-up estimate from the Agriculture agent's irrigation/fertilizer/
   pesticide requirements.
3. Explicit crop-reference fallback values when the input lacks quantities.

No LLM participates in these calculations.
"""
from __future__ import annotations

import csv
import os
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.schemas import CropRecommendation, IndicateursFinanciers


# Reference fallbacks are deliberately kept outside app/data/mock_*. They are
# used only when neither an external cost dataset nor usable Agriculture
# quantities are available, and are labelled as fallbacks in every response.
_REFERENCE_TOTAL_COST_EUR_HA = {
    "tomate": 9500.0,
    "pomme_de_terre": 4200.0,
    "ble": 950.0,
    "ble_tendre": 950.0,
    "ble_dur": 1100.0,
    "mais": 1400.0,
    "tournesol": 650.0,
    "colza": 1150.0,
    "orge": 850.0,
}

# Fixed operations, seed and machinery component used by the bottom-up model.
_FIXED_OPERATIONS_EUR_HA = {
    "tomate": 5200.0,
    "pomme_de_terre": 2600.0,
    "ble": 560.0,
    "ble_tendre": 560.0,
    "ble_dur": 620.0,
    "mais": 760.0,
    "tournesol": 430.0,
    "colza": 650.0,
    "orge": 520.0,
}
_DEFAULT_FIXED_OPERATIONS_EUR_HA = 600.0

# Transparent reference unit costs. They can be overridden without code
# changes and are intentionally exposed in the calculation detail.
N_EUR_PER_KG = float(os.getenv("BUSINESS_N_EUR_PER_KG", "1.10"))
P_EUR_PER_KG = float(os.getenv("BUSINESS_P_EUR_PER_KG", "1.25"))
K_EUR_PER_KG = float(os.getenv("BUSINESS_K_EUR_PER_KG", "0.85"))
IRRIGATION_EUR_PER_MM_HA = float(os.getenv("BUSINESS_IRRIGATION_EUR_PER_MM_HA", "1.20"))
PESTICIDE_TREATMENT_EUR_HA = float(os.getenv("BUSINESS_PESTICIDE_TREATMENT_EUR_HA", "85"))


def normalize_crop(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip().replace("-", "_").replace(" ", "_")


def _walk_numbers(value: Any, prefix: str = "") -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            found.extend(_walk_numbers(child, child_prefix))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        found.append((prefix.lower(), float(value)))
    return found


def _first_number(data: dict, aliases: tuple[str, ...]) -> float | None:
    for path, value in _walk_numbers(data):
        if any(alias in path for alias in aliases):
            return value
    return None


@lru_cache(maxsize=1)
def _external_cost_rows() -> dict[str, dict]:
    path_value = os.getenv("BUSINESS_COST_DATA_CSV", "").strip()
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.is_file():
        return {}

    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            culture = row.get("culture") or row.get("crop") or ""
            raw_cost = row.get("cost_per_ha_eur") or row.get("cout_eur_par_ha")
            if not culture or raw_cost is None:
                continue
            try:
                cost = float(str(raw_cost).replace(",", "."))
            except ValueError:
                continue
            if cost <= 0:
                continue
            rows[normalize_crop(culture)] = {
                "cost": cost,
                "source": row.get("source") or path.name,
                "year": row.get("year") or row.get("annee"),
            }
    return rows


@dataclass(frozen=True)
class CostEstimate:
    cost_per_ha: float
    source: str
    is_fallback: bool
    components: dict[str, float]
    confidence: float
    reasons: list[str]


def estimate_production_cost(crop: CropRecommendation) -> CostEstimate:
    key = normalize_crop(crop.culture)
    external = _external_cost_rows().get(key)
    if external:
        year = f", {external['year']}" if external.get("year") else ""
        return CostEstimate(
            cost_per_ha=round(external["cost"], 2),
            source=f"{external['source']}{year}",
            is_fallback=False,
            components={"external_total_eur_ha": round(external["cost"], 2)},
            confidence=0.95,
            reasons=["Coût total par hectare issu du jeu de données configuré."],
        )

    n_kg = _first_number(crop.besoins_engrais, ("n_dose_kg_ha", "azote_kg_ha"))
    p_kg = _first_number(crop.besoins_engrais, ("phosphore_kg_ha", "p_kg_ha"))
    k_kg = _first_number(crop.besoins_engrais, ("potassium_kg_ha", "k_kg_ha"))
    irrigation_mm = _first_number(
        crop.besoins_irrigation, ("irrigation_need_mm", "besoin_irrigation_mm", "mm_total")
    )
    treatments = _first_number(
        crop.besoins_pesticides, ("traitements_par_saison", "nombre_traitements")
    )

    supplied = [n_kg, p_kg, k_kg, irrigation_mm, treatments]
    if any(value is not None for value in supplied):
        components = {
            "operations_semences_materiel_eur_ha": _FIXED_OPERATIONS_EUR_HA.get(
                key, _DEFAULT_FIXED_OPERATIONS_EUR_HA
            ),
            "azote_eur_ha": max(n_kg or 0.0, 0.0) * N_EUR_PER_KG,
            "phosphore_eur_ha": max(p_kg or 0.0, 0.0) * P_EUR_PER_KG,
            "potassium_eur_ha": max(k_kg or 0.0, 0.0) * K_EUR_PER_KG,
            "irrigation_eur_ha": max(irrigation_mm or 0.0, 0.0) * IRRIGATION_EUR_PER_MM_HA,
            "protection_cultures_eur_ha": max(treatments or 0.0, 0.0)
            * PESTICIDE_TREATMENT_EUR_HA,
        }
        total = round(sum(components.values()), 2)
        completeness = sum(value is not None for value in supplied) / len(supplied)
        return CostEstimate(
            cost_per_ha=total,
            source="Calcul agronomique AgriAdvisor à partir des besoins Agriculture",
            is_fallback=False,
            components={k: round(v, 2) for k, v in components.items()},
            confidence=round(0.55 + 0.30 * completeness, 2),
            reasons=[
                "Coût reconstruit à partir des besoins d'intrants de la parcelle.",
                "Les prix unitaires sont des références configurables, pas des devis fournisseurs.",
            ],
        )

    fallback = _REFERENCE_TOTAL_COST_EUR_HA.get(key, 1000.0)
    return CostEstimate(
        cost_per_ha=fallback,
        source="Barème de référence de secours AgriAdvisor",
        is_fallback=True,
        components={"reference_total_eur_ha": fallback},
        confidence=0.30,
        reasons=["Aucune quantité d'intrant exploitable; barème de secours utilisé."],
    )


def compute_financial_indicators(
    *,
    area_ha: float,
    available_area_ha: float,
    yield_kg_ha: float,
    price_eur_kg: float,
    production_cost_eur_ha: float,
    mitigation_cost_eur_ha: float,
    budget_eur: float,
    cost_source: str,
    cost_fallback: bool,
) -> IndicateursFinanciers:
    if area_ha <= 0:
        raise ValueError("area_ha doit être positif")
    if min(yield_kg_ha, price_eur_kg, production_cost_eur_ha, mitigation_cost_eur_ha) < 0:
        raise ValueError("Les rendements, prix et coûts ne peuvent pas être négatifs")

    revenue_per_ha = yield_kg_ha * price_eur_kg
    total_cost_per_ha = production_cost_eur_ha + mitigation_cost_eur_ha
    gross_revenue = revenue_per_ha * area_ha
    total_cost = total_cost_per_ha * area_ha
    profit = gross_revenue - total_cost
    margin = (profit / gross_revenue * 100.0) if gross_revenue > 0 else -100.0
    roi = (profit / total_cost * 100.0) if total_cost > 0 else 0.0
    breakeven_price = total_cost_per_ha / yield_kg_ha if yield_kg_ha > 0 else None
    breakeven_yield = total_cost_per_ha / price_eur_kg if price_eur_kg > 0 else None
    full_available_cost = total_cost_per_ha * available_area_ha
    budget_gap = max(0.0, full_available_cost - budget_eur)

    return IndicateursFinanciers(
        revenu_brut_estime_eur=round(gross_revenue, 2),
        cout_total_estime_eur=round(total_cost, 2),
        profit_estime_eur=round(profit, 2),
        profit_margin_pct=round(margin, 2),
        roi_pct=round(roi, 2),
        prix_seuil_rentabilite_eur_par_kg=(
            round(breakeven_price, 4) if breakeven_price is not None else None
        ),
        rendement_seuil_kg_par_ha=(
            round(breakeven_yield, 2) if breakeven_yield is not None else None
        ),
        budget_suffisant=budget_eur >= full_available_cost,
        budget_gap_eur=round(budget_gap, 2),
        cout_production_eur_par_ha=round(production_cost_eur_ha, 2),
        cout_mitigation_eur_par_ha=round(mitigation_cost_eur_ha, 2),
        cout_total_eur_par_ha=round(total_cost_per_ha, 2),
        source_cout=cost_source,
        cout_fallback=cost_fallback,
    )
