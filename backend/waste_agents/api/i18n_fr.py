"""
Lightweight French labels for waste / process / product names stored in English
in the knowledge base. Unknown terms keep a cleaned Title Case fallback.
"""
from __future__ import annotations

import re

_TERM_FR: dict[str, str] = {
    # plant parts / wastes
    "husk": "balle",
    "hull": "enveloppe",
    "bran": "son",
    "straw": "paille",
    "stalk": "tige",
    "stem": "tige",
    "leaf": "feuille",
    "leaves": "feuilles",
    "peel": "peau",
    "pod": "cosse",
    "pulp": "pulpe",
    "pomace": "marc",
    "bagasse": "bagasse",
    "stover": "canne / résidus de tiges",
    "chaff": "balle / menue paille",
    "cob": "rafle",
    "meal": "tourteau",
    "residue": "résidu",
    "residues": "résidus",
    "shell": "coque",
    "root": "racine",
    "head": "capitule",
    "grain": "grain",
    "ash": "cendre",
    # processes
    "pyrolysis": "pyrolyse",
    "composting": "compostage",
    "fermentation": "fermentation",
    "anaerobic digestion": "méthanisation",
    "gasification": "gazéification",
    "combustion": "combustion",
    "hydrolysis": "hydrolyse",
    "extraction": "extraction",
    "pelleting": "granulation",
    "torrefaction": "torréfaction",
    "carbonization": "carbonisation",
    "chemical activation": "activation chimique",
    # products
    "biochar": "biochar",
    "biogas": "biogaz",
    "bioethanol": "bioéthanol",
    "biodiesel": "biodiesel",
    "compost": "compost",
    "activated carbon": "charbon actif",
    "animal feed": "alimentation animale",
    "fertilizer": "engrais",
    "fertiliser": "engrais",
    "silica": "silice",
    "mulch": "paillage",
    "bedding": "litière",
    "pellets": "granulés",
    "briquettes": "briquettes",
    # crop prefixes often left in English waste names
    "wheat": "blé",
    "maize": "maïs",
    "corn": "maïs",
    "barley": "orge",
    "rapeseed": "colza",
    "sunflower": "tournesol",
    "potato": "pomme de terre",
    "sugar beet": "betterave",
    "soybean": "soja",
    "pea": "pois",
    "tomato": "tomate",
    "rice": "riz",
}


def label_fr(text: str) -> str:
    """Best-effort French label for a waste / process / product string."""
    raw = (text or "").strip()
    if not raw:
        return ""
    key = raw.lower()
    if key in _TERM_FR:
        return _TERM_FR[key].capitalize() if _TERM_FR[key][0].islower() else _TERM_FR[key]

    # Phrase-level known replacements first (multi-word keys)
    out = key
    for en, fr in sorted(_TERM_FR.items(), key=lambda kv: -len(kv[0])):
        if " " in en or len(en) > 4:
            out = re.sub(rf"\b{re.escape(en)}\b", fr, out)

    # Remaining single tokens
    parts = re.split(r"(\s|/|-)", out)
    translated: list[str] = []
    for part in parts:
        low = part.lower()
        if low in _TERM_FR:
            translated.append(_TERM_FR[low])
        else:
            translated.append(part)
    result = "".join(translated).strip()
    # Title-ish: capitalize first letter only
    if result:
        return result[0].upper() + result[1:]
    return raw
