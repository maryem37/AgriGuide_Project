"""
Reference €/kg prices and average yields per hectare.

Agreste IPPAP provides a *price index* (base 100), not absolute euro prices.
Until a live RNM feed is wired, we keep calibrated regional baselines for
prix/rendement and overlay the real IPPAP trend on top.
"""

from __future__ import annotations

from app.market_intelligence.crop_aliases import normalize_culture_key

# Calibrated French market baselines (order-of-magnitude, not live quotes).
_BASELINES: dict[str, dict] = {
    "tomate": {
        "prix_moyen_eur_par_kg": 0.85,
        "rendement_moyen_kg_par_ha": 65000,
    },
    "pomme_de_terre": {
        "prix_moyen_eur_par_kg": 0.28,
        "rendement_moyen_kg_par_ha": 38000,
    },
    "ble": {
        "prix_moyen_eur_par_kg": 0.22,
        "rendement_moyen_kg_par_ha": 7200,
    },
    "ble_tendre": {
        "prix_moyen_eur_par_kg": 0.22,
        "rendement_moyen_kg_par_ha": 7200,
    },
    "ble_dur": {
        "prix_moyen_eur_par_kg": 0.28,
        "rendement_moyen_kg_par_ha": 5500,
    },
    "mais": {
        "prix_moyen_eur_par_kg": 0.19,
        "rendement_moyen_kg_par_ha": 9500,
    },
    "tournesol": {
        "prix_moyen_eur_par_kg": 0.48,
        "rendement_moyen_kg_par_ha": 2800,
    },
    "colza": {
        "prix_moyen_eur_par_kg": 0.45,
        "rendement_moyen_kg_par_ha": 3200,
    },
    "orge": {
        "prix_moyen_eur_par_kg": 0.18,
        "rendement_moyen_kg_par_ha": 6500,
    },
}

_DEFAULT = {
    "prix_moyen_eur_par_kg": 0.30,
    "rendement_moyen_kg_par_ha": 5000,
}


def get_baseline(culture: str) -> dict:
    key = normalize_culture_key(culture)
    return dict(_BASELINES.get(key, _DEFAULT))
