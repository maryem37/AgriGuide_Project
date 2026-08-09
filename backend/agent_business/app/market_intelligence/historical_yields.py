"""Optional, unit-aware FAOSTAT historical-yield provider.

The service uses a configured CSV when available and otherwise returns None,
letting the existing reference yield act as an explicit fallback.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.market_intelligence.crop_aliases import normalize_culture_key


_FAO_ITEM = {
    "mais": "maize (corn)",
    "ble": "wheat",
    "ble_tendre": "wheat",
    "ble_dur": "wheat, durum",
    "orge": "barley",
    "tournesol": "sunflower seed",
    "colza": "rape or colza seed",
    "pomme_de_terre": "potatoes",
    "tomate": "tomatoes",
}


def _candidate_paths() -> list[Path]:
    configured = os.getenv("BUSINESS_FAO_YIELD_CSV", "").strip()
    paths = [Path(configured)] if configured else []
    # Development migration path; production should set BUSINESS_FAO_YIELD_CSV.
    paths.append(
        Path(__file__).resolve().parents[2]
        / "profit_analysis"
        / "csv"
        / "Crops and livestock products__ Average yield_hisorical yiels trends_production trends_harvested area.csv"
    )
    return paths


@lru_cache(maxsize=1)
def _load() -> tuple[pd.DataFrame | None, Path | None]:
    path = next((p for p in _candidate_paths() if p.is_file()), None)
    if path is None:
        return None, None
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return None, None
    required = {"Area", "Item", "Element", "Value", "Year", "Unit"}
    if not required.issubset(frame.columns):
        return None, None
    frame["Value"] = pd.to_numeric(frame["Value"], errors="coerce")
    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    return frame.dropna(subset=["Value", "Year"]), path


def _to_kg_ha(value: float, unit: str) -> float | None:
    normalized = unit.strip().lower().replace(" ", "")
    if normalized in {"kg/ha", "kgperha"}:
        return value
    if normalized in {"hg/ha", "100g/ha"}:
        return value / 10.0
    if normalized in {"t/ha", "tonnes/ha", "tonne/ha"}:
        return value * 1000.0
    return None


def get_historical_yield(culture: str, area: str = "France", years: int = 5) -> dict | None:
    frame, path = _load()
    if frame is None or path is None:
        return None

    key = normalize_culture_key(culture)
    target = _FAO_ITEM.get(key)
    if not target:
        return None

    rows = frame[
        frame["Item"].astype(str).str.strip().str.lower().eq(target)
        & frame["Area"].astype(str).str.strip().str.lower().eq(area.lower())
        & frame["Element"].astype(str).str.strip().str.lower().eq("yield")
    ].sort_values("Year")
    if rows.empty:
        return None

    converted: list[float] = []
    used_years: list[int] = []
    for _, row in rows.tail(years).iterrows():
        value = _to_kg_ha(float(row["Value"]), str(row["Unit"]))
        if value is not None:
            converted.append(value)
            used_years.append(int(row["Year"]))
    if not converted:
        return None

    series = pd.Series(converted, dtype=float)
    return {
        "yield_kg_ha": round(float(series.mean()), 2),
        "std_kg_ha": round(float(series.std()), 2) if len(series) > 1 else 0.0,
        "years": used_years,
        "source": f"FAOSTAT historique ({path.name})",
    }
