"""
Map AgriGuide culture keys (Agriculture agent / Business mocks) to Agreste
IPPAP search terms and human-readable labels.
"""

from __future__ import annotations

import unicodedata

# Preferred IPPAP product substrings (matched against stripped product names).
# Order matters only when multiple could match — we pick the most specific
# hierarchy level in price_trends anyway.
_CROP_SEARCH_TERMS: dict[str, list[str]] = {
    "tomate": ["tomate"],
    "pomme_de_terre": ["pomme de terre"],
    "ble": ["ble tendre", "ble"],
    "ble_tendre": ["ble tendre"],
    "ble_dur": ["ble dur"],
    "mais": ["mais"],
    "tournesol": ["tournesol"],
    "colza": ["colza"],
    "orge": ["orge"],
    "soja": ["soja"],
    "avoine": ["avoine"],
    "sorgho": ["sorgho"],
    "betterave": ["betterave"],
    "lin": ["lin"],
}


def strip_accents(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize_culture_key(culture: str) -> str:
    key = strip_accents(culture).lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "blé": "ble",
        "blé_tendre": "ble_tendre",
        "maïs": "mais",
        "pomme de terre": "pomme_de_terre",
        "pdt": "pomme_de_terre",
    }
    return aliases.get(key, key)


def search_terms_for(culture: str) -> list[str]:
    """Return accent-stripped lowercase substrings to look up in IPPAP."""
    key = normalize_culture_key(culture)
    terms = _CROP_SEARCH_TERMS.get(key)
    if terms:
        return terms
    # Fallback: humanized culture key
    return [key.replace("_", " ")]


def display_name(culture: str) -> str:
    key = normalize_culture_key(culture)
    labels = {
        "tomate": "Tomate",
        "pomme_de_terre": "Pomme de terre",
        "ble": "Blé",
        "ble_tendre": "Blé tendre",
        "ble_dur": "Blé dur",
        "mais": "Maïs",
        "tournesol": "Tournesol",
        "colza": "Colza",
        "orge": "Orge",
    }
    return labels.get(key, culture.replace("_", " ").capitalize())
