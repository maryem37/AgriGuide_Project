"""
Parse Agreste IPPAP CSV exports (FDS_IPPAP_YYYY.csv) into a normalized DataFrame.

Raw columns (semicolon-separated):
  ANNREF, IPPAP_DIM2_LIB, IPPAP_DIM3_MOD, IPPAP_DIM3_LIB, VALEUR, QUALITE, …

Product hierarchy is encoded as leading underscores in IPPAP_DIM2_LIB, e.g.:
  ___Cereales (production)          → niveau 3
  ____Ble tendre                    → niveau 4
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_MONTH_NAME_TO_NUM = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}


def _niveau_hierarchie(label: str) -> int:
    if not isinstance(label, str):
        return 0
    n = 0
    for ch in label:
        if ch == "_":
            n += 1
        else:
            break
    return n


def _mois_num(row: pd.Series) -> int | None:
    mod = row.get("IPPAP_DIM3_MOD")
    if pd.notna(mod):
        try:
            return int(str(mod).strip())
        except ValueError:
            pass
    lib = str(row.get("IPPAP_DIM3_LIB") or "").strip().lower()
    return _MONTH_NAME_TO_NUM.get(lib)


def parse_ippap_csv(path: str | Path) -> pd.DataFrame:
    """
    Load one Agreste IPPAP file and return columns expected by price_trends:
      produit_nom, annee, mois_num, valeur, qualite, niveau_hierarchie
    """
    path = Path(path)
    df = pd.read_csv(path, sep=";", encoding="utf-8", low_memory=False)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "produit_nom",
                "annee",
                "mois_num",
                "valeur",
                "qualite",
                "niveau_hierarchie",
            ]
        )

    out = pd.DataFrame()
    out["produit_nom"] = (
        df["IPPAP_DIM2_LIB"]
        .astype(str)
        .str.lstrip("_")
        .str.strip()
    )
    out["annee"] = pd.to_numeric(df["ANNREF"], errors="coerce").astype("Int64")
    out["mois_num"] = df.apply(_mois_num, axis=1).astype("Int64")
    out["valeur"] = pd.to_numeric(df["VALEUR"], errors="coerce")
    out["qualite"] = df["QUALITE"].astype(str).str.strip().str.upper()
    out["niveau_hierarchie"] = df["IPPAP_DIM2_LIB"].map(_niveau_hierarchie)

    out = out.dropna(subset=["produit_nom", "annee", "mois_num", "valeur"])
    out["annee"] = out["annee"].astype(int)
    out["mois_num"] = out["mois_num"].astype(int)
    return out.reset_index(drop=True)
