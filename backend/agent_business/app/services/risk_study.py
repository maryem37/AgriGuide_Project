"""
Service Risk Study.

Calcule un risque_score_normalise (0 à 1) = probabilite * impact.
C'est un calcul déterministe, pas une estimation LLM — le LLM n'intervient
que plus tard pour reformuler la description en langage naturel si besoin
(dans le narrative service, pas ici).
"""

from app.data.mock_risks import get_mock_crop_risk
from app.models.schemas import EtudeRisque, CropRecommendation


def evaluer_risque(crop: CropRecommendation) -> EtudeRisque:
    risk_data = get_mock_crop_risk(crop.culture)

    risque_score = round(risk_data["probabilite"] * risk_data["impact"], 3)

    return EtudeRisque(
        risque_principal=risk_data["risque_principal"],
        description=risk_data["description"],
        probabilite=risk_data["probabilite"],
        impact=risk_data["impact"],
        risque_score_normalise=risque_score,
        solution_mitigation=risk_data["solution_mitigation"],
        cout_mitigation_eur_par_ha=risk_data["cout_mitigation_eur_par_ha"],
    )
