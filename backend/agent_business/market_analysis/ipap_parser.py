"""
ippap_parser.py
Parses raw FranceAgriMer/Agreste IPPAP CSV exports (semicolon-delimited,
one row per year/product/period) into a tidy DataFrame.

Raw column layout: each IPPAP_DIMn triplet is a generic "dimension" the
export format uses. The DIMn column just names the dimension, the _LIB
column holds the actual human-readable label, and _MOD is an internal code.

    IPPAP_DIM1 / IPPAP_DIM1_LIB / IPPAP_DIM1_MOD  -> indicator (always "Indice Ippap...")
    IPPAP_DIM2 / IPPAP_DIM2_LIB / IPPAP_DIM2_MOD  -> product   (IPPAP_DIM2_LIB = product name)
    IPPAP_DIM3 / IPPAP_DIM3_LIB / IPPAP_DIM3_MOD  -> period    (IPPAP_DIM3_LIB = "Janvier".."Decembre"
                                                                  or "Moyenne annuelle", DIM3_MOD = "001".."013")
"""

from pathlib import Path
import unicodedata

import pandas as pd

MONTH_MAP = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}

REQUIRED_COLUMNS = {
    "ANNREF", "IPPAP_DIM2_LIB", "IPPAP_DIM3_LIB", "VALEUR", "QUALITE",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _read_raw(csv_path: Path) -> pd.DataFrame:
    """Reads the raw semicolon-delimited export, trying utf-8 first then
    falling back to the cp1252 / latin-1 encodings these government exports
    sometimes use."""
    last_err = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(csv_path, sep=";", encoding=encoding)
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise RuntimeError(
        f"Could not decode {csv_path.name} with utf-8, cp1252, or latin-1."
    ) from last_err


def parse_ippap_csv(csv_path: Path, include_annual_average: bool = False) -> pd.DataFrame:
    """
    Parses one raw IPPAP CSV export into a tidy DataFrame with columns:
        produit_nom, annee, mois_num, valeur, qualite

    include_annual_average:
        If False (default), rows where the period is "Moyenne annuelle"
        (an annual average, not a real month) are dropped -- they have no
        real mois_num and would otherwise pollute month-level trend queries.
        If True, they're kept with mois_num = <NA>.
    """
    csv_path = Path(csv_path)
    df = _read_raw(csv_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path.name}: missing expected columns {missing}")

    out = pd.DataFrame()
    out["produit_nom"] = df["IPPAP_DIM2_LIB"].astype(str).str.strip()
    out["annee"] = pd.to_numeric(df["ANNREF"], errors="coerce").astype("Int64")

    period_label = df["IPPAP_DIM3_LIB"].astype(str).str.strip()
    period_key = period_label.apply(lambda s: _strip_accents(s).lower())
    out["mois_num"] = period_key.map(MONTH_MAP).astype("Int64")  # <NA> for "Moyenne annuelle" etc.

    # VALEUR: handle both "120.9" and "120,9" style decimals just in case.
    out["valeur"] = pd.to_numeric(
        df["VALEUR"].astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )

    out["qualite"] = df["QUALITE"].astype(str).str.strip()

    if not include_annual_average:
        out = out[out["mois_num"].notna()]

    out = out.dropna(subset=["produit_nom", "annee", "valeur"])
    out = out.reset_index(drop=True)

    return out


if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("FDS_IPPAP_2021.csv")
    result = parse_ippap_csv(path)
    print(result.head(10))
    print(f"\n{len(result)} rows parsed from {path.name}")