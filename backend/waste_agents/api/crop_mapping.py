"""
Map AgriGuide agriculture culture keys (French snake_case) to waste_agents
canonical English crop names used in canonical_knowledge.json.
"""
from __future__ import annotations

# Agriculture ML keys (agent_agriculture) + mock/business aliases → KB name
CULTURE_TO_KB: dict[str, str] = {
    "ble_tendre": "Wheat",
    "ble": "Wheat",
    "mais": "Maize",
    "colza": "Rapeseed",
    "orge": "Barley",
    "tournesol": "Sunflower",
    "pomme_de_terre": "Potato",
    "betterave_sucriere": "Sugar Beet",
    "soja": "Soybean",
    "pois_proteagineux": "Pea",
    "tomate": "Tomato",
    "riz": "Rice",
    "cafe": "Coffee",
    "banane": "Banana",
}

# Friendly French crop labels (UI). Falls back to agriculture cultureLabel on FE.
KB_CROP_LABEL_FR: dict[str, str] = {
    "Wheat": "Blé",
    "Maize": "Maïs",
    "Rapeseed": "Colza",
    "Barley": "Orge",
    "Sunflower": "Tournesol",
    "Potato": "Pomme de terre",
    "Sugar Beet": "Betterave sucrière",
    "Soybean": "Soja",
    "Pea": "Pois",
    "Tomato": "Tomate",
    "Rice": "Riz",
    "Coffee": "Café",
    "Banana": "Banane",
}


def normalize_culture_key(culture: str) -> str:
    return (
        culture.strip()
        .lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("ô", "o")
        .replace(" ", "_")
        .replace("-", "_")
    )


def culture_to_kb_name(culture: str) -> str | None:
    """Return the KB crop name for an agri culture key, or None if unmapped."""
    key = normalize_culture_key(culture)
    if key in CULTURE_TO_KB:
        return CULTURE_TO_KB[key]
    # Already an English KB name?
    titled = culture.strip()
    return titled if titled else None
