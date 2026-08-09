"""
Distribution mensuelle de l'IPPAP (2020-2026).

Montre, pour chaque mois de l'annee (Janvier a Decembre), la distribution
des valeurs de l'indice observees sur les 7 annees -> utile pour reperer
la saisonnalite des prix (ex: est-ce que tel mois est structurellement
plus haut ou plus bas ?).

Installation :
    pip install pandas matplotlib

Utilisation :
    python distribution_mensuelle.py
"""

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("C:/Users/malek/Desktop/agri-business-advisor/backend/data/market/agreste/ippap_2020_2026_clean.csv")

MOIS_NOMS = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin",
             "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]

# ------------------------------------------------------------------
# Choix du produit a analyser : ici l'indice general (code 1).
# Pour analyser une autre culture, change PRODUIT_CODE
# (voir la liste des codes dans ippap_2020_2026_clean.csv, colonne
# produit_code / produit_nom).
# ------------------------------------------------------------------
PRODUIT_CODE = 1
PRODUIT_NOM = "Indice general"

data = df[
    (df["type"] == "indice") &
    (df["produit_code"] == PRODUIT_CODE) &
    (df["mois_num"] <= 12)  # on exclut "Moyenne annuelle" (mois_num=13)
].copy()

# une liste de valeurs par mois (une valeur par annee, donc 7 points par mois)
valeurs_par_mois = [
    data.loc[data["mois_num"] == m, "valeur"].values for m in range(1, 13)
]

plt.figure(figsize=(11, 6))
plt.boxplot(valeurs_par_mois, labels=MOIS_NOMS, showmeans=True)

# on superpose les points individuels (une couleur par annee) pour voir
# le detail derriere chaque boite
for _, row in data.iterrows():
    plt.scatter(row["mois_num"], row["valeur"], alpha=0.5, color="steelblue", s=20)

plt.title(f"Distribution mensuelle - {PRODUIT_NOM} (2020-2026)")
plt.xlabel("Mois")
plt.ylabel("Indice")
plt.grid(True, alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig("5_distribution_mensuelle.png")
plt.show()

# petit resume chiffre
resume = data.groupby("mois_num")["valeur"].agg(["mean", "std", "min", "max"])
resume.index = MOIS_NOMS
print(resume.round(2))