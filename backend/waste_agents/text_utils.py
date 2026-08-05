"""
Shared text-normalization helpers.

`singularize()` is used in two places that matter for data quality:
1. Crop-name normalization (agents/validator.py) -- different sources
   write "Tomato" or "Tomatoes" for the same crop. Without convergence,
   the wastes split across two separate crop entries and the UI never
   finds either one complete.
2. Waste-name canonicalization (agents/validator.py) -- "Tomato Peel" and
   "Tomato Peels" must merge into one entity.

Kept as a small, hand-written heuristic rather than a NLP dependency
(inflect, spaCy): the vocabulary this project needs to singularize --
crop and plant-part names -- is narrow and predictable, so a bounded
exception list is cheaper and more auditable than a general-purpose
library.
"""
from __future__ import annotations

# Irregular plurals that naive "-s" stripping would mangle.
IRREGULAR_PLURALS = {
    "leaves": "leaf",
    "knives": "knife",
    "shelves": "shelf",
}

# Words ending in "s" that are already singular. Naive "-s" stripping
# mangles them ("asparagus" -> "asparagu"), and several are crop or
# residue names this project handles directly.
INVARIANT_SINGULARS = {
    "asparagus", "citrus", "molasses", "bagasse", "pomace", "grass",
    "rice", "maize", "analysis", "basis", "series", "species", "hummus",
    "couscous", "cactus", "fungus", "humus", "campus", "virus", "focus",
    "bonus", "status", "census", "lens", "news",
}


def singularize(term: str) -> str:
    """
    Naive singularization, sufficient for plant-part and crop vocabulary.

    Exists so that a crop or waste named in the plural by one source
    matches the singular used by another ("Tomatoes" and "Tomato" are one
    crop). Handles the irregular plurals that matter here, guards the
    words that merely end in "s" without being plural, and otherwise
    strips a trailing "s".
    """
    t = term.strip().lower()
    if t in INVARIANT_SINGULARS:
        return t
    if t in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[t]
    # Multi-word terms: singularize only the final word (e.g. "fruit stalks")
    if " " in t:
        head, _, tail = t.rpartition(" ")
        return f"{head} {singularize(tail)}".strip()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    # "tomatoes" -> "tomato", "potatoes" -> "potato"
    if t.endswith("oes") and len(t) > 4:
        return t[:-2]
    # "bunches" -> "bunch", "boxes" -> "box", "grasses" -> "grass"
    if t.endswith(("ches", "shes", "xes", "sses", "zes")) and len(t) > 4:
        return t[:-2]
    # Latin-derived singulars ("citrus", "asparagus") are not plurals, and
    # "-ss" endings ("grass") never are either.
    if t.endswith("us") or t.endswith("ss") or len(t) <= 3:
        return t
    if t.endswith("s"):
        return t[:-1]
    return t
