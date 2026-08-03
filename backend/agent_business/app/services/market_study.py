"""
Service Market Study.

Estime, pour une culture donnée : le prix probable, le rendement attendu,
la date de récolte, et le profit brut par hectare.

Les tendances de prix viennent d'Agreste IPPAP (indices réels). Les prix €/kg
et rendements utilisent un barème de référence tant que le flux RNM live
n'est pas branché — voir app/market_intelligence/.
"""

from datetime import date, timedelta

from app.market_intelligence import get_market_price
from app.models.schemas import EtudeMarche, CropRecommendation


def estimer_marche(crop: CropRecommendation, date_plantation: date) -> EtudeMarche:
    """
    Construit l'étude de marché d'une culture :
    - prix + rendement (barème de référence) ajustés par tendance Agreste
    - date de récolte estimée = date_plantation + cycle_jours
    - profit brut par hectare = rendement * prix ajusté
    """
    prix_data = get_market_price(crop.culture)

    date_recolte_estimee = date_plantation + timedelta(days=crop.cycle_jours)

    rendement_kg_ha = prix_data["rendement_moyen_kg_par_ha"]
    prix_kg = prix_data["prix_moyen_eur_par_kg"]

    # Ajustement du prix selon la tendance de marché (+/- jusqu'à 15%)
    prix_ajuste = prix_kg * (1 + prix_data["tendance"] * 0.15)

    profit_brut_par_ha = rendement_kg_ha * prix_ajuste

    return EtudeMarche(
        prix_moyen_eur_par_kg=round(prix_ajuste, 3),
        rendement_estime_kg_par_ha=rendement_kg_ha,
        tendance_prix=prix_data["tendance"],
        date_recolte_estimee=date_recolte_estimee,
        profit_brut_par_ha=round(profit_brut_par_ha, 2),
        source=prix_data["source"],
        indice_pct_change=prix_data.get("indice_pct_change"),
        latest_index=prix_data.get("latest_index"),
        produit_agreste=prix_data.get("produit_agreste"),
        justification_marche=prix_data.get("justification"),
        market_score=prix_data.get("market_score"),
        tendance_label=prix_data.get("tendance_label"),
        demande=prix_data.get("demande"),
        concurrence=prix_data.get("concurrence"),
    )
