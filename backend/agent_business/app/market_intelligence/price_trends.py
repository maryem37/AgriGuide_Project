"""
Compute Agreste IPPAP price-index trends for a crop (pandas only, no LLM).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.market_intelligence.crop_aliases import search_terms_for, strip_accents
from app.market_intelligence.ipap_parser import parse_ippap_csv
from app.market_intelligence.paths import list_ippap_csvs, resolve_market_data_dir

CROP_COLUMN = "produit_nom"
YEAR_COLUMN = "annee"
MONTH_COLUMN = "mois_num"
PRICE_COLUMN = "valeur"
HIERARCHY_COLUMN = "niveau_hierarchie"

_csv_df: pd.DataFrame | None = None


def resolve_agreste_dir() -> Path | None:
    """Backward-compatible alias — same folder as market PDFs/CSVs."""
    return resolve_market_data_dir()


def _load_csv() -> pd.DataFrame:
    global _csv_df
    if _csv_df is not None:
        return _csv_df

    csv_files = list_ippap_csvs()
    if not csv_files:
        print("[market_intelligence] No Agreste CSV files found — trends unavailable.")
        _csv_df = pd.DataFrame()
        return _csv_df

    frames: list[pd.DataFrame] = []
    for f in csv_files:
        try:
            frames.append(parse_ippap_csv(f))
        except Exception as e:
            print(f"[market_intelligence] Could not parse {f.name}: {e}")

    if not frames:
        _csv_df = pd.DataFrame()
        return _csv_df

    _csv_df = pd.concat(frames, ignore_index=True)
    _csv_df["_produit_norm"] = (
        _csv_df[CROP_COLUMN].astype(str).apply(strip_accents).str.lower()
    )
    print(
        f"[market_intelligence] Loaded {len(_csv_df)} IPPAP rows from {csv_files[0].parent} "
        f"({len(csv_files)} file(s))."
    )
    return _csv_df


def clear_cache() -> None:
    """Reset cached DataFrame (useful in tests)."""
    global _csv_df
    _csv_df = None


def compute_price_trend(crop_name: str, months: int = 6) -> dict | None:
    """
    Return a price INDEX trend for the crop, or None if no CSV match.

    Keys: data_points, pct_change, latest_index, produit_label
    """
    df = _load_csv()
    if df.empty or "_produit_norm" not in df.columns:
        return None

    matches = pd.DataFrame()
    term_norm = ""
    for term in search_terms_for(crop_name):
        term_norm = strip_accents(term).lower()
        hit = df[df["_produit_norm"].str.contains(term_norm, case=False, na=False, regex=False)]
        if not hit.empty:
            matches = hit
            break

    if matches.empty:
        return None

    if "qualite" in matches.columns:
        validated = matches[matches["qualite"].astype(str).str.upper() == "OUI"]
        if not validated.empty:
            matches = validated

    # Prefer an exact product-label match over a deep subcategory.
    if term_norm:
        exact = matches[matches["_produit_norm"] == term_norm]
        if not exact.empty:
            matches = exact
        elif HIERARCHY_COLUMN in matches.columns and matches[CROP_COLUMN].nunique() > 1:
            specific = matches[matches[HIERARCHY_COLUMN] >= 3]
            pool = specific if not specific.empty else matches
            best_level = pool[HIERARCHY_COLUMN].min()
            best_label = pool[pool[HIERARCHY_COLUMN] == best_level][CROP_COLUMN].iloc[0]
            matches = matches[matches[CROP_COLUMN] == best_label]
    elif HIERARCHY_COLUMN in matches.columns and matches[CROP_COLUMN].nunique() > 1:
        max_level = matches[HIERARCHY_COLUMN].max()
        best_label = matches[matches[HIERARCHY_COLUMN] == max_level][CROP_COLUMN].iloc[0]
        matches = matches[matches[CROP_COLUMN] == best_label]

    produit_label = str(matches[CROP_COLUMN].iloc[0]) if not matches.empty else crop_name

    if YEAR_COLUMN in matches.columns and MONTH_COLUMN in matches.columns:
        matches = matches.copy()
        matches["_sort_key"] = matches[YEAR_COLUMN] * 100 + matches[MONTH_COLUMN]
        matches = matches.sort_values("_sort_key")

    if PRICE_COLUMN not in matches.columns:
        return {
            "data_points": len(matches),
            "pct_change": None,
            "latest_index": None,
            "produit_label": produit_label,
        }

    recent = matches.tail(months)
    if len(recent) < 2:
        latest = recent[PRICE_COLUMN].iloc[-1] if len(recent) else None
        return {
            "data_points": len(matches),
            "pct_change": None,
            "latest_index": latest,
            "produit_label": produit_label,
        }

    first_val = recent[PRICE_COLUMN].iloc[0]
    last_val = recent[PRICE_COLUMN].iloc[-1]
    pct_change = None
    if first_val not in (None, 0) and pd.notna(first_val) and pd.notna(last_val):
        pct_change = round(float((last_val - first_val) / first_val * 100), 1)

    return {
        "data_points": len(matches),
        "pct_change": pct_change,
        "latest_index": float(last_val) if pd.notna(last_val) else None,
        "produit_label": produit_label,
    }


def pct_change_to_tendance(pct_change: float | None, scale_pct: float = 15.0) -> float:
    """Map a 6-month index % change to tendance in [-1, 1]."""
    if pct_change is None:
        return 0.0
    return max(-1.0, min(1.0, round(pct_change / scale_pct, 3)))
