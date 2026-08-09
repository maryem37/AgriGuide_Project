"""
csv_retriever.py
-----------------
Structured-data retrieval layer for the profit-analysis RAG pipeline.

We deliberately do NOT vector-embed these CSVs. They are structured/tabular
(INSEE price indices in wide year-columns format, FAO yield data in long
format). Pandas filtering is faster, exact, and avoids embedding numbers
into a vector space where similarity search is meaningless. Only the PDFs
go through the docling + embedding path (see embedder.py).

Handles three known formats from the project:
  1. caracteristiques.csv          -> metadata / catalog of INSEE series (idBank -> product, unit, frequency...)
  2. valeurs_annuelles.csv /
     valeurs_mensuelles.csv        -> INSEE wide format: one row per series, one column per year/period,
                                       PLUS an interleaved "Codes" flag row after every data row that must be dropped.
  3. Crops and livestock products...csv (FAO/FAOSTAT) -> long format, one row per
                                       (Area, Item, Element, Year) with a Value column.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _normalize(text: str) -> str:
    """Lowercase + strip accents, for fuzzy/robust matching of French crop/product names."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower().strip()


def _read_insee_csv(path: str | Path) -> pd.DataFrame:
    """INSEE exports are ';'-delimited, quote-heavy, and often UTF-8 with BOM."""
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)


# --------------------------------------------------------------------------- #
# 1. caracteristiques.csv  (series catalog)
# --------------------------------------------------------------------------- #

@dataclass
class SeriesInfo:
    id_bank: str
    product: str
    zone: str
    unit: str
    periodicity: str


def load_caracteristiques(path: str | Path) -> pd.DataFrame:
    """
    Loads the INSEE series catalog.
    Returns a DataFrame indexed by idBank with clean column names.
    """
    df = _read_insee_csv(path)
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "idBank": "id_bank",
        "Nomenclature de l'indice des prix agricoles": "product",
        "Zone géographique": "zone",
        "Unité": "unit",
        "Périodicité": "periodicity",
        "Indicateur": "indicator",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    keep = [c for c in ["id_bank", "product", "zone", "unit", "periodicity", "indicator"] if c in df.columns]
    df = df[keep].copy()
    df["product_norm"] = df["product"].map(_normalize)
    return df.set_index("id_bank", drop=False)


def find_series_for_product(catalog: pd.DataFrame, product_keyword: str) -> pd.DataFrame:
    """Fuzzy substring match on product name, e.g. 'ble' matches 'Semences de blé tendre hybride'."""
    kw = _normalize(product_keyword)
    return catalog[catalog["product_norm"].str.contains(kw, na=False)]


# --------------------------------------------------------------------------- #
# 2. valeurs_annuelles.csv / valeurs_mensuelles.csv (INSEE wide format)
# --------------------------------------------------------------------------- #

def load_insee_wide_values(path: str | Path) -> pd.DataFrame:
    """
    Parses INSEE wide-format price index files into tidy long format:
    columns -> [label, id_bank, period, value]

    Key quirk handled: every real data row is immediately followed by a
    "Codes" row (quality-flag row, e.g. "A" = official value) that must be
    dropped, not treated as a second series.
    """
    df = _read_insee_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Drop flag rows: their "Libellé" is literally "Codes"
    label_col = "Libellé"
    df = df[df[label_col].str.strip().str.lower() != "codes"].copy()

    id_col = "idBank"
    meta_cols = {label_col, id_col, "Dernière mise à jour", "Période"}
    year_cols = [c for c in df.columns if c not in meta_cols]

    long_df = df.melt(
        id_vars=[label_col, id_col],
        value_vars=year_cols,
        var_name="period",
        value_name="value",
    )

    # Blank cells arrive as "" (string) -> NaN, then to float
    long_df["value"] = long_df["value"].replace("", pd.NA)
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.dropna(subset=["value"]).reset_index(drop=True)

    long_df = long_df.rename(columns={label_col: "label", id_col: "id_bank"})
    long_df["period"] = long_df["period"].astype(str)
    return long_df[["label", "id_bank", "period", "value"]]


def get_price_index(
    values_df: pd.DataFrame,
    catalog: pd.DataFrame,
    product_keyword: str,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """
    Joins the catalog (to resolve a product keyword -> id_bank) with the
    values table, optionally filtered to one period/year.
    """
    matches = find_series_for_product(catalog, product_keyword)
    if matches.empty:
        return pd.DataFrame(columns=["label", "id_bank", "period", "value"])

    ids = matches["id_bank"].tolist()
    result = values_df[values_df["id_bank"].isin(ids)].copy()
    if period is not None:
        result = result[result["period"] == str(period)]
    return result.sort_values("period")


def latest_price_index(values_df: pd.DataFrame, catalog: pd.DataFrame, product_keyword: str) -> Optional[float]:
    """Convenience: most recent available value for a product's index series."""
    rows = get_price_index(values_df, catalog, product_keyword)
    if rows.empty:
        return None
    rows = rows.sort_values("period")
    return float(rows.iloc[-1]["value"])


# --------------------------------------------------------------------------- #
# 3. FAO yield / production / area harvested (long format)
# --------------------------------------------------------------------------- #

def load_fao_data(path: str | Path) -> pd.DataFrame:
    """FAOSTAT-style export: plain comma CSV, already long/tidy."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    return df


def get_yield_history(
    fao_df: pd.DataFrame,
    crop: str,
    area: str = "France",
    element: str = "Yield",
) -> pd.DataFrame:
    """
    element in {"Yield", "Production", "Area harvested"}.
    Returns rows sorted by year for the matched crop.
    """
    crop_norm = _normalize(crop)
    mask = (
        fao_df["Item"].map(_normalize).str.contains(crop_norm, na=False)
        & (fao_df["Area"].map(_normalize) == _normalize(area))
        & (fao_df["Element"] == element)
    )
    return fao_df[mask].sort_values("Year")


def estimate_expected_yield(
    fao_df: pd.DataFrame,
    crop: str,
    area: str = "France",
    n_recent_years: int = 5,
) -> dict:
    """
    Simple statistical baseline yield estimator (this is the fallback / feature
    source for the predictive model — see predictive_yield.py).
    FAO 'Yield' unit is typically '100 g/ha' or 'hg/ha' -> converted to t/ha.

    Returns dict with mean, std, n_points, unit_note, confidence_hint.
    """
    hist = get_yield_history(fao_df, crop, area, element="Yield")
    if hist.empty:
        return {
            "mean_t_per_ha": None,
            "std_t_per_ha": None,
            "n_points": 0,
            "confidence_hint": "low",
        }

    recent = hist.tail(n_recent_years)
    # FAO yield values are usually in 100g/ha (hectograms/ha); 1 t/ha = 10000 hg/ha
    values_t_ha = recent["Value"] / 10000.0

    return {
        "mean_t_per_ha": float(values_t_ha.mean()),
        "std_t_per_ha": float(values_t_ha.std()) if len(values_t_ha) > 1 else 0.0,
        "n_points": int(len(values_t_ha)),
        "years_used": recent["Year"].tolist(),
        "confidence_hint": "high" if len(values_t_ha) >= 3 else "medium" if len(values_t_ha) >= 1 else "low",
    }


# --------------------------------------------------------------------------- #
# Quick self-test when run directly
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    from config import (
        CARACTERISTIQUES_CSV,
        VALEURS_ANNUELLES_CSV,
        VALEURS_MENSUELLES_CSV,
        FAO_YIELD_CSV,
    )

    print("=== caractéristiques.csv ===")
    catalog = load_caracteristiques(CARACTERISTIQUES_CSV)
    print(catalog[["id_bank", "product", "zone", "unit", "periodicity"]])

    print("\n=== valeurs_annuelles.csv (long form, 'Codes' rows dropped) ===")
    annual = load_insee_wide_values(VALEURS_ANNUELLES_CSV)
    print(annual)
    assert not (annual["label"].str.lower() == "codes").any(), "Codes rows leaked through!"

    print("\n=== price index lookup: 'IPAMPA' total, latest (annual) ===")
    latest = latest_price_index(annual, catalog, "IPAMPA")
    print("Latest IPAMPA total index:", latest)
    assert latest == 124.7

    print("\n=== valeurs_mensuelles.csv (same wide-parser, monthly periods) ===")
    monthly = load_insee_wide_values(VALEURS_MENSUELLES_CSV)
    print(monthly.head())
    assert not (monthly["label"].str.lower() == "codes").any(), "Codes rows leaked through!"

    print("\n=== FAO yield/production/area (long format, real filename) ===")
    fao = load_fao_data(FAO_YIELD_CSV)
    print(fao)
    est = estimate_expected_yield(fao, "Almonds")
    print("Estimated yield:", est)

    print("\nAll self-tests passed against real filenames.")