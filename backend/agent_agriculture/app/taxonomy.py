"""
Standardize crop codes and names across the pipeline.
Maps RPG codes (e.g., BTH, MIS) and user inputs (e.g., 'ble') to standard internal keys (e.g., 'ble_tendre').

Ported as-is from the standalone `agri-advisor-parcelle` prototype.
"""

def normalize_crop(code: str | None) -> str | None:
    if not code:
        return None

    c = code.strip().lower()

    # Wheat
    if c in ["bth", "btp", "ble", "blé", "ble tendre", "blé tendre", "ble_tendre"]:
        return "ble_tendre"
    # Corn
    elif c in ["mis", "mid", "mie", "mais", "maïs"]:
        return "mais"
    # Rapeseed
    elif c in ["czh", "czp", "colza"]:
        return "colza"
    # Barley
    elif c in ["orh", "orp", "orge"]:
        return "orge"
    # Sunflower
    elif c in ["trn", "tournesol"]:
        return "tournesol"
    # Potato — crop-pool expansion
    elif c in ["pdt", "pomme de terre", "pomme_de_terre", "patate"]:
        return "pomme_de_terre"
    # Sugar beet — crop-pool expansion. RPG's "btr"/"btn" cover beet
    # generally (industrial/sugar/fodder are not always distinguished in
    # RPG declarations); normalized to the sugar-beet key since that's
    # this project's scored variant.
    elif c in ["btr", "btn", "bts", "betterave", "betterave sucriere", "betterave sucrière", "betterave_sucriere"]:
        return "betterave_sucriere"
    # Soybean — crop-pool expansion
    elif c in ["soj", "soja"]:
        return "soja"
    # Field pea (protein pea) — crop-pool expansion. RPG's "pvt" (pois)
    # covers pea generally; normalized to the protein-pea key since
    # that's this project's scored variant.
    elif c in ["pvt", "poi", "pois", "pois proteagineux", "pois protéagineux", "pois_proteagineux"]:
        return "pois_proteagineux"

    return c.replace(" ", "_")


_DISPLAY_NAMES = {
    # Normalized core crops
    "ble_tendre": "Blé tendre",
    "mais": "Maïs",
    "colza": "Colza",
    "orge": "Orge",
    "tournesol": "Tournesol",
    "pomme_de_terre": "Pomme de terre",
    "betterave_sucriere": "Betterave sucrière",
    "soja": "Soja",
    "pois_proteagineux": "Pois protéagineux",

    # Common RPG fallback codes (when not normalized to core)
    "ptr": "Prairie temporaire",
    "pph": "Prairie permanente",
    "luz": "Luzerne",
    "fra": "Fraise",
    "sai": "Sainfoin",
    "sne": "Seigle",
    "jac": "Jachère",
    "ail": "Ail",
    "fla": "Fléole",
    "sog": "Sorgho",
    "pep": "Pépinière",
    "epi": "Épeautre",
    "mlg": "Mélange (céréales)",
    "lbf": "Légumineuses",
    "rdi": "Radis",
    "bdh": "Blé dur d'hiver",
    "vrc": "Vigne",
    "vrg": "Verger",
    "soj": "Soja",
    "pdt": "Pomme de terre",
    "btr": "Betterave",
    "lin": "Lin",
    "pvt": "Pois",
}


def get_display_name(code: str) -> str:
    """Returns a human-readable name for a given internal or RPG crop code."""
    if not code:
        return "Inconnu"

    clean_code = code.strip().lower()
    if clean_code in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[clean_code]

    # Formatting fallback for unknown codes: capitalize and replace underscores
    return code.replace("_", " ").capitalize()
