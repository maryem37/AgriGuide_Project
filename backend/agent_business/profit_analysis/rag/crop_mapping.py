"""
crop_mapping.py
-----------------
Bridges farmer-entered crop names (French, informal: "mais", "blé", "ble tendre")
to the English item names used in the FAO CSV ("Maize (corn)", "Wheat").

Without this, a farmer typing "mais" never matches "Maize (corn)" via plain
substring search, silently zeroing out the yield estimate and cascading into
a broken report (zero revenue, meaningless margin, inflated risk masking).

Strategy:
  1. Exact/known mapping first (fast, reliable for common crops).
  2. Fuzzy match against the actual Item column as a fallback, so crops not
     in the hardcoded table still have a chance instead of failing silently.
"""

from __future__ import annotations

import difflib
import unicodedata
from typing import Optional

import pandas as pd


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower().strip()


# Common French crop names -> keyword(s) expected in the FAO "Item" column.
# Extend this table as you discover more mismatches in your real data.
FR_TO_FAO_KEYWORDS: dict[str, str] = {
    "mais": "maize",
    "ble": "wheat",
    "ble tendre": "wheat",
    "ble dur": "wheat, durum",
    "orge": "barley",
    "avoine": "oats",
    "colza": "rape or colza seed",
    "tournesol": "sunflower",
    "pomme de terre": "potatoes",
    "betterave": "sugar beet",
    "betterave sucriere": "sugar beet",
    "vigne": "grapes",
    "raisin": "grapes",
    "olive": "olives",
    "amande": "almonds",
    "amandes": "almonds",
    "riz": "rice",
    "soja": "soya beans",
    "luzerne": "lucerne",
    "pois": "peas, dry",
}


def resolve_crop_to_fao_item(
    crop_input: str,
    fao_items: pd.Series,
    fuzzy_cutoff: float = 0.6,
) -> Optional[str]:
    """
    Returns the best-matching FAO 'Item' string for a farmer's crop input,
    or None if nothing reasonable is found.

    fao_items: the fao_df["Item"] column (all rows, not deduplicated is fine).
    """
    crop_norm = _normalize(crop_input)
    unique_items = fao_items.dropna().unique().tolist()
    items_norm = {item: _normalize(item) for item in unique_items}

    # 1. Direct substring match on the raw input (handles crops already in English/exact form)
    for item, item_norm in items_norm.items():
        if crop_norm and crop_norm in item_norm:
            return item

    # 2. Known French -> FAO keyword mapping
    keyword = FR_TO_FAO_KEYWORDS.get(crop_norm)
    if keyword:
        keyword_norm = _normalize(keyword)
        for item, item_norm in items_norm.items():
            if keyword_norm in item_norm:
                return item

    # 3. Fuzzy match as last resort (handles typos, unseen crops)
    candidates = difflib.get_close_matches(
        crop_norm, list(items_norm.values()), n=1, cutoff=fuzzy_cutoff
    )
    if candidates:
        # map back from normalized form to the original Item string
        for item, item_norm in items_norm.items():
            if item_norm == candidates[0]:
                return item

    return None


if __name__ == "__main__":
    # Self-test against a small fake FAO item list
    fake_items = pd.Series([
        "Maize (corn)", "Wheat", "Almonds, in shell", "Olives", "Grapes", "Rice",
    ])

    tests = {
        "mais": "Maize (corn)",
        "Mais": "Maize (corn)",
        "ble": "Wheat",
        "amandes": "Almonds, in shell",
        "Almonds": "Almonds, in shell",
        "xyzcropdoesnotexist": None,
    }

    for crop_in, expected in tests.items():
        result = resolve_crop_to_fao_item(crop_in, fake_items)
        status = "OK" if result == expected else "FAIL"
        print(f"[{status}] '{crop_in}' -> {result} (expected {expected})")
        assert result == expected, f"Mismatch for '{crop_in}'"

    print("\nAll crop-mapping self-tests passed.")