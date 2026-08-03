"""
Service Scenario Generator — orchestre market_study + risk_study + scoring
pour produire les N scénarios finaux (3 par défaut), triés par matching_score.

C'est ce service que le endpoint FastAPI appelle directement.
"""

from datetime import date

from app.data.mock_production_costs import get_mock_production_cost_per_ha
from app.models.schemas import (
    BusinessAdvisorRequest,
    BusinessScenario,
    CropRecommendation,
    DetailCalculMetrique,
    DetailCalculScenario,
)
from app.services.market_study import estimer_marche
from app.services.risk_study import evaluer_risque
from app.services.scoring import (
    POIDS_BUDGET_FIT,
    POIDS_PROFIT,
    POIDS_RISQUE,
    CandidatScoring,
    ScoreDetail,
    calculer_matching_scores_detailles,
)


def _construire_candidat(
    crop: CropRecommendation,
    date_plantation: date,
    budget_input: float,
) -> tuple[CandidatScoring, dict]:
    """
    Calcule toutes les données intermédiaires pour une culture, et retourne :
    - le candidat prêt pour le scoring
    - un dict de données brutes réutilisées pour construire le scénario final
      ET le détail de calcul explicable
    """
    etude_marche = estimer_marche(crop, date_plantation)
    etude_risque = evaluer_risque(crop)

    cout_production_par_ha = get_mock_production_cost_per_ha(crop.culture)
    cout_total_par_ha = cout_production_par_ha + etude_risque.cout_mitigation_eur_par_ha

    profit_net_par_ha = etude_marche.profit_brut_par_ha - cout_total_par_ha
    superficie_max_financable_ha = round(budget_input / cout_total_par_ha, 2)

    candidat = CandidatScoring(
        culture=crop.culture,
        profit_net_par_ha=profit_net_par_ha,
        risque_normalise=etude_risque.risque_score_normalise,
        superficie_max_financable_ha=superficie_max_financable_ha,
    )

    donnees_brutes = {
        "etude_marche": etude_marche,
        "etude_risque": etude_risque,
        "cycle_jours": crop.cycle_jours,
        "date_plantation": date_plantation,
        "cout_production_par_ha": cout_production_par_ha,
        "cout_total_par_ha": cout_total_par_ha,
        "profit_net_par_ha": profit_net_par_ha,
        "superficie_max_financable_ha": superficie_max_financable_ha,
    }

    return candidat, donnees_brutes


def _construire_detail_calcul(
    culture: str,
    donnees: dict,
    score_detail: ScoreDetail,
    superficie_disponible_ha: float,
    superficie_conseillee_ha: float,
    profit_estime: float,
) -> DetailCalculScenario:
    """Construit l'explication pas-à-pas de chaque métrique affichée pour ce scénario."""
    etude_marche = donnees["etude_marche"]
    etude_risque = donnees["etude_risque"]

    score_matching = DetailCalculMetrique(
        formule=(
            "score = w1 * profit_normalisé + w2 * (1 - risque_normalisé) + w3 * fit_budget, "
            "puis ramené sur 100. Normalisation min-max du profit net/ha sur toutes les "
            "cultures candidates. Calcul déterministe (le LLM n'intervient pas ici)."
        ),
        valeurs={
            "poids_profit_w1": POIDS_PROFIT,
            "poids_risque_w2": POIDS_RISQUE,
            "poids_budget_w3": POIDS_BUDGET_FIT,
            "profit_normalise": score_detail.profit_normalise,
            "risque_normalise": score_detail.risque_normalise,
            "fit_budget": score_detail.fit_budget,
            "matching_score": score_detail.score,
        },
        sources=["Formule interne AgriAdvisor — backend/agent_business/app/services/scoring.py"],
    )

    surface_conseillee = DetailCalculMetrique(
        formule=(
            "superficie_max_financable_ha = budget_input / cout_total_par_ha ; "
            "superficie_conseillee_ha = min(superficie_disponible_ha, superficie_max_financable_ha)"
        ),
        valeurs={
            "budget_input_eur": donnees.get("budget_input"),
            "cout_production_eur_par_ha": donnees["cout_production_par_ha"],
            "cout_mitigation_eur_par_ha": etude_risque.cout_mitigation_eur_par_ha,
            "cout_total_eur_par_ha": donnees["cout_total_par_ha"],
            "superficie_max_financable_ha": donnees["superficie_max_financable_ha"],
            "superficie_disponible_ha": superficie_disponible_ha,
            "superficie_conseillee_ha": superficie_conseillee_ha,
        },
        sources=[
            "Barème de coûts de production simulé — app/data/mock_production_costs.py",
            "Budget renseigné par l'agriculteur (budget_input)",
        ],
    )

    rendement_estime = DetailCalculMetrique(
        formule="rendement_estime_kg_par_ha = rendement moyen historique de la culture (source marché).",
        valeurs={
            "culture": culture,
            "rendement_estime_kg_par_ha": etude_marche.rendement_estime_kg_par_ha,
        },
        sources=[etude_marche.source],
    )

    recolte_estimee = DetailCalculMetrique(
        formule="date_recolte_estimee = date_plantation_prevue + cycle_jours (cycle propre à la culture)",
        valeurs={
            "date_plantation_prevue": donnees["date_plantation"].isoformat(),
            "cycle_jours": donnees["cycle_jours"],
            "date_recolte_estimee": etude_marche.date_recolte_estimee.isoformat(),
        },
        sources=["crop_recommendations de l'agent Agriculture (cycle_jours par culture)"],
    )

    profit_estime_detail = DetailCalculMetrique(
        formule=(
            "profit_brut_par_ha = rendement_estime_kg_par_ha * prix_ajusté ; "
            "profit_net_par_ha = profit_brut_par_ha - (cout_production_par_ha + cout_mitigation_eur_par_ha) ; "
            "profit_estime = profit_net_par_ha * superficie_conseillee_ha"
        ),
        valeurs={
            "prix_moyen_eur_par_kg_ajuste": etude_marche.prix_moyen_eur_par_kg,
            "tendance_prix": etude_marche.tendance_prix,
            "rendement_estime_kg_par_ha": etude_marche.rendement_estime_kg_par_ha,
            "profit_brut_eur_par_ha": etude_marche.profit_brut_par_ha,
            "cout_total_eur_par_ha": donnees["cout_total_par_ha"],
            "profit_net_eur_par_ha": donnees["profit_net_par_ha"],
            "superficie_conseillee_ha": superficie_conseillee_ha,
            "profit_estime_eur": profit_estime,
        },
        sources=[
            etude_marche.source,
            "Barème de coûts de production simulé — app/data/mock_production_costs.py",
            "Étude de risque (coût de mitigation) — app/data/mock_risks.py",
        ],
    )
    if etude_marche.indice_pct_change is not None:
        profit_estime_detail.valeurs["indice_agreste_pct_6m"] = etude_marche.indice_pct_change
    if etude_marche.justification_marche:
        profit_estime_detail.valeurs["justification_marche"] = etude_marche.justification_marche
    if etude_marche.demande:
        profit_estime_detail.valeurs["demande"] = etude_marche.demande
    if etude_marche.concurrence:
        profit_estime_detail.valeurs["concurrence"] = etude_marche.concurrence
    if etude_marche.market_score is not None:
        profit_estime_detail.valeurs["market_score_rag"] = etude_marche.market_score

    return DetailCalculScenario(
        score_matching=score_matching,
        surface_conseillee=surface_conseillee,
        rendement_estime=rendement_estime,
        recolte_estimee=recolte_estimee,
        profit_estime=profit_estime_detail,
    )


def generer_scenarios(request: BusinessAdvisorRequest) -> list[BusinessScenario]:
    candidats: list[CandidatScoring] = []
    donnees_par_culture: dict[str, dict] = {}

    for crop in request.crop_recommendations:
        candidat, donnees = _construire_candidat(
            crop, request.date_plantation_prevue, request.budget_input
        )
        donnees["budget_input"] = request.budget_input
        candidats.append(candidat)
        donnees_par_culture[crop.culture] = donnees

    scores_detailles = calculer_matching_scores_detailles(candidats, request.superficie_disponible_ha)

    # Tri par matching_score décroissant, on garde les N meilleurs
    cultures_triees = sorted(scores_detailles.items(), key=lambda x: x[1].score, reverse=True)
    top_cultures = cultures_triees[: request.nb_scenarios]

    scenarios: list[BusinessScenario] = []
    for culture, score_detail in top_cultures:
        donnees = donnees_par_culture[culture]
        etude_marche = donnees["etude_marche"]
        etude_risque = donnees["etude_risque"]

        superficie_conseillee_ha = round(
            min(request.superficie_disponible_ha, donnees["superficie_max_financable_ha"]), 2
        )
        profit_estime = round(donnees["profit_net_par_ha"] * superficie_conseillee_ha, 2)

        detail_calcul = _construire_detail_calcul(
            culture=culture,
            donnees=donnees,
            score_detail=score_detail,
            superficie_disponible_ha=request.superficie_disponible_ha,
            superficie_conseillee_ha=superficie_conseillee_ha,
            profit_estime=profit_estime,
        )

        scenarios.append(
            BusinessScenario(
                terrain_id=request.terrain_id,
                budget_input=request.budget_input,
                culture=culture,
                quantite_par_ha=etude_marche.rendement_estime_kg_par_ha,
                profit_estime=profit_estime,
                risque_score=etude_risque.risque_score_normalise,
                risque_description=f"{etude_risque.risque_principal} — {etude_risque.description}",
                solution_risque=etude_risque.solution_mitigation,
                matching_score=score_detail.score,
                etude_marche=etude_marche.model_dump(mode="json"),
                superficie_max_financable_ha=donnees["superficie_max_financable_ha"],
                superficie_conseillee_ha=superficie_conseillee_ha,
                detail_calcul=detail_calcul,
            )
        )

    return scenarios
