"""Business Heuristic Risk Study (internal AgriGuide methodology V1).

Calculates operational scenario risk from agronomical incompatibility, market downside,
yield variability and cost uncertainty. This heuristic is internal to AgriGuide and distinct
from the evidence-based climate risk model (Belhsen et al., 2026).
"""

from app.models.schemas import CropRecommendation, EtudeMarche, EtudeRisque
from app.services.financial_service import CostEstimate, _first_number


def evaluer_risque(
    crop: CropRecommendation,
    marche: EtudeMarche,
    cout: CostEstimate,
) -> EtudeRisque:
    """Combine Agriculture compatibility, market downside, historical yield
    variability and cost-data quality (Internal Business Heuristic V1)."""
    incompatibilite = max(0.0, min(1.0, 1.0 - crop.score_compatibilite / 100.0))
    baisse_marche = max(0.0, -marche.tendance_prix)
    volatilite_rendement = 0.0
    if marche.rendement_std_kg_par_ha and marche.rendement_estime_kg_par_ha > 0:
        volatilite_rendement = min(
            1.0, marche.rendement_std_kg_par_ha / marche.rendement_estime_kg_par_ha
        )
    incertitude_cout = 1.0 - cout.confidence

    probabilite = min(
        1.0,
        0.45 * incompatibilite
        + 0.25 * baisse_marche
        + 0.20 * volatilite_rendement
        + 0.10 * incertitude_cout,
    )
    # A low Agriculture compatibility makes a realized incident more damaging.
    impact = min(1.0, 0.35 + 0.45 * incompatibilite + 0.20 * baisse_marche)
    risque_score = round(probabilite * impact, 3)

    raisons = [
        f"Compatibilité agronomique Agriculture: {crop.score_compatibilite:.1f}/100.",
        f"Signal de tendance de prix: {marche.tendance_prix:.3f} (-1 à 1).",
    ]
    if marche.rendement_std_kg_par_ha is not None:
        raisons.append(
            f"Variabilité historique du rendement: {marche.rendement_std_kg_par_ha:.0f} kg/ha."
        )
    if cout.is_fallback:
        raisons.append("Coût de production de secours: incertitude financière accrue.")

    treatments = _first_number(
        crop.besoins_pesticides, ("traitements_par_saison", "nombre_traitements")
    ) or 0.0
    mitigation_cost = round(max(35.0, treatments * 35.0), 2)

    factors = {
        "Adéquation agronomique": incompatibilite,
        "Baisse de marché": baisse_marche,
        "Volatilité du rendement": volatilite_rendement,
        "Incertitude des coûts": incertitude_cout,
    }
    principal = max(factors, key=factors.get)
    solutions = {
        "Adéquation agronomique": "Réduire la surface initiale et confirmer par un diagnostic agronomique.",
        "Baisse de marché": "Sécuriser un débouché ou un prix contractuel avant le semis.",
        "Volatilité du rendement": "Prévoir une marge de sécurité et adapter irrigation/assurance récolte.",
        "Incertitude des coûts": "Demander des devis fournisseurs avant confirmation définitive.",
    }

    return EtudeRisque(
        risque_principal=principal,
        description="Score d'heuristique d'affaires interne V1 (Agriculture, marché, coût) — distinct du modèle climatique Belhsen et al. (2026).",
        probabilite=round(probabilite, 3),
        impact=round(impact, 3),
        risque_score_normalise=risque_score,
        solution_mitigation=solutions[principal],
        cout_mitigation_eur_par_ha=mitigation_cost,
        raisons=raisons,
        sources=[
            "score_compatibilite et besoins de l'agent Agriculture",
            marche.source,
            cout.source,
        ],
        donnees_reelles=not cout.is_fallback,
    )
