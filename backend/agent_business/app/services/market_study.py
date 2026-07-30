"""
Service Market Study.

Estime, pour une culture donnée : le prix probable, le rendement attendu,
la date de récolte, et le profit brut par hectare.

L'estimation temporelle suit exactement la logique décrite dans le projet :
si on cultive une tomate, la récolte est estimée à N jours après la
plantation (le cycle_jours vient de l'agent Agriculture).
"""

from datetime import date, timedelta

from app.data.mock_market_prices import get_mock_market_price
from app.models.schemas import EtudeMarche, CropRecommendation


def estimer_marche(crop: CropRecommendation, date_plantation: date) -> EtudeMarche:
    """
    Construit l'étude de marché d'une culture :
    - prix + rendement (source RNM/FranceAgriMer, simulée pour l'instant)
    - date de récolte estimée = date_plantation + cycle_jours
    - profit brut par hectare = rendement * prix (avant coûts, le net est
      calculé plus loin dans le scénario final avec les besoins/mitigation)
    """
    prix_data = get_mock_market_price(crop.culture)

    date_recolte_estimee = date_plantation + timedelta(days=crop.cycle_jours)

    rendement_kg_ha = prix_data["rendement_moyen_kg_par_ha"]
    prix_kg = prix_data["prix_moyen_eur_par_kg"]

    # Ajustement simple du prix selon la tendance de marché (+/- jusqu'à 15%)
    prix_ajuste = prix_kg * (1 + prix_data["tendance"] * 0.15)

    profit_brut_par_ha = rendement_kg_ha * prix_ajuste

    return EtudeMarche(
        prix_moyen_eur_par_kg=round(prix_ajuste, 3),
        rendement_estime_kg_par_ha=rendement_kg_ha,
        tendance_prix=prix_data["tendance"],
        date_recolte_estimee=date_recolte_estimee,
        profit_brut_par_ha=round(profit_brut_par_ha, 2),
        source=prix_data["source"],
    )
