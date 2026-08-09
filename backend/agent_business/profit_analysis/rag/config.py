"""
config.py
----------
Central place for the exact, real filenames used in backend/data/csv/.
Import these constants instead of retyping long/accented filenames in every
script — one typo in "caractéristiques.csv" or the FAO file's long name
will silently return an empty DataFrame instead of an error, since
pandas.read_csv on a wrong path raises FileNotFoundError but a wrong path
built from a slightly-off string is an easy mistake to make more than once.
"""

from pathlib import Path

# Keep data paths portable when the project is moved or cloned elsewhere.
# config.py lives in backend/profit_analysis/rag, while the CSV assets live in
# backend/profit_analysis/csv.
DATA_CSV_DIR = Path(__file__).resolve().parents[1] / "csv"

CARACTERISTIQUES_CSV = DATA_CSV_DIR / "caractéristiques.csv"
VALEURS_ANNUELLES_CSV = DATA_CSV_DIR / "valeurs_annuelles.csv"
VALEURS_MENSUELLES_CSV = DATA_CSV_DIR / "valeurs_mensuelles.csv"
FAO_YIELD_CSV = (
    DATA_CSV_DIR
    / "Crops and livestock products__ Average yield_hisorical yiels trends_production trends_harvested area.csv"
)


def check_all_present() -> dict:
    """Quick existence check for all four expected files. Useful to run once after cloning/moving the repo."""
    paths = {
        "caractéristiques.csv": CARACTERISTIQUES_CSV,
        "valeurs_annuelles.csv": VALEURS_ANNUELLES_CSV,
        "valeurs_mensuelles.csv": VALEURS_MENSUELLES_CSV,
        "FAO yield/production/area csv": FAO_YIELD_CSV,
    }
    return {name: p.exists() for name, p in paths.items()}


if __name__ == "__main__":
    for name, exists in check_all_present().items():
        status = "FOUND" if exists else "MISSING"
        print(f"[{status}] {name}")
