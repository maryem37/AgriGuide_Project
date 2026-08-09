"""
Fusionne les fichiers FDS_IPPAP_2020.csv ... FDS_IPPAP_2026.csv en une seule
base de données propre, en "long format", prête à être utilisée comme source
pour des analyses ou pour un LLM (RAG / function-calling).

Installation :
    pip install pandas

Utilisation :
    python fusionner_ippap.py
    -> génère ippap_2020_2026_clean.csv
"""

import pandas as pd
import glob
import os

MOIS_ORDRE = {
    "Janvier": 1, "Fevrier": 2, "Mars": 3, "Avril": 4, "Mai": 5, "Juin": 6,
    "Juillet": 7, "Aout": 8, "Septembre": 9, "Octobre": 10, "Novembre": 11,
    "Decembre": 12, "Moyenne annuelle": 13,
}

INDICATEUR_LABELS = {1: "indice", 2: "ponderation"}

def charger_et_fusionner(dossier="."):
    fichiers = sorted(glob.glob(os.path.join(dossier, "FDS_IPPAP_*.csv")))
    if not fichiers:
        raise FileNotFoundError("Aucun fichier FDS_IPPAP_*.csv trouve dans " + dossier)

    frames = [pd.read_csv(f, sep=";") for f in fichiers]
    df = pd.concat(frames, ignore_index=True)

    # Colonnes utiles, renommees en clair
    df = df.rename(columns={
        "ANNREF": "annee",
        "IPPAP_DIM1_MOD": "type_code",
        "IPPAP_DIM2_MOD": "produit_code",
        "IPPAP_DIM2_LIB": "produit_libelle",
        "IPPAP_DIM3_LIB": "periode_libelle",
        "VALEUR": "valeur",
        "QUALITE": "qualite",
    })

    df["type"] = df["type_code"].map(INDICATEUR_LABELS)
    df["mois_num"] = df["periode_libelle"].map(MOIS_ORDRE)
    # nettoyage du libelle produit (les prefixes "_" indiquent le niveau
    # hierarchique dans la nomenclature ; on le garde en colonne separee)
    df["niveau_hierarchie"] = df["produit_libelle"].str.count(r"^_+")
    df["produit_nom"] = df["produit_libelle"].str.lstrip("_")

    colonnes_finales = [
        "annee", "mois_num", "periode_libelle", "type",
        "produit_code", "produit_nom", "niveau_hierarchie",
        "valeur", "qualite",
    ]
    df_clean = df[colonnes_finales].sort_values(
        ["produit_code", "annee", "mois_num"]
    ).reset_index(drop=True)

    return df_clean


if __name__ == "__main__":
    df_clean = charger_et_fusionner(".")
    df_clean.to_csv("ippap_2020_2026_clean.csv", index=False)
    print(f"{len(df_clean)} lignes -> ippap_2020_2026_clean.csv")
    print(f"Annees couvertes : {sorted(df_clean['annee'].unique())}")
    print(f"Produits distincts : {df_clean['produit_code'].nunique()}")