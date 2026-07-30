"""
Démo bout-en-bout de l'agent Business, sans serveur FastAPI, pour valider
toute la chaîne : données simulées -> scénarios -> décision du farmer ->
rapport final.

Exécution : python -m app.tests.demo_pipeline (depuis backend/agent_business/)
"""

import json
from datetime import date

from app.data.mock_crop_recommendations import (
    get_mock_crop_recommendations,
    MOCK_TERRAIN_ID,
    MOCK_TERRAIN_SUPERFICIE_HA,
    MOCK_DATE_PLANTATION,
)
from app.models.schemas import (
    BusinessAdvisorRequest,
    CropRecommendation,
    FarmerDecisionRequest,
    AllocationChoisie,
)
from app.services.scenario_generator import generer_scenarios
from app.services.decision_service import confirmer_decision


def run_demo():
    print("=" * 70)
    print("ÉTAPE A — Chargement des données simulées (crop_recommendations)")
    print("=" * 70)
    crops_raw = get_mock_crop_recommendations()
    crops = [CropRecommendation(**c) for c in crops_raw]
    for c in crops:
        print(f"  - {c.culture} (score agri: {c.score_compatibilite}, cycle: {c.cycle_jours}j)")

    print("\n" + "=" * 70)
    print("ÉTAPE B — Requête Business Advisor (budget du farmer)")
    print("=" * 70)
    budget_farmer = 25000.0  # exemple : 25 000 EUR de budget disponible
    request = BusinessAdvisorRequest(
        terrain_id=MOCK_TERRAIN_ID,
        superficie_disponible_ha=MOCK_TERRAIN_SUPERFICIE_HA,
        budget_input=budget_farmer,
        date_plantation_prevue=MOCK_DATE_PLANTATION,
        crop_recommendations=crops,
        nb_scenarios=3,
    )
    print(f"  Budget : {budget_farmer} EUR | Superficie disponible : {MOCK_TERRAIN_SUPERFICIE_HA} ha")

    print("\n" + "=" * 70)
    print("ÉTAPE C — Génération des 3 scénarios (market study + risk study + scoring)")
    print("=" * 70)
    scenarios = generer_scenarios(request)
    for s in scenarios:
        print(f"\n  >>> Scénario : {s.culture.upper()} (matching_score = {s.matching_score}/100)")
        print(f"      Quantité estimée / ha : {s.quantite_par_ha:,.0f} kg")
        print(f"      Superficie conseillée : {s.superficie_conseillee_ha} ha "
              f"(max finançable : {s.superficie_max_financable_ha} ha)")
        print(f"      Profit estimé : {s.profit_estime:,.2f} EUR")
        print(f"      Risque : {s.risque_description}")
        print(f"      Solution : {s.solution_risque}")

    print("\n" + "=" * 70)
    print("ÉTAPE D — Human-in-the-loop : le farmer choisit sa répartition finale")
    print("=" * 70)
    # Exemple : le farmer choisit tomate (3 ha) + pomme de terre (3 ha) sur 13 ha
    scenario_par_culture = {s.culture: s for s in scenarios}
    allocations = []
    if "tomate" in scenario_par_culture:
        allocations.append(
            AllocationChoisie(scenario_id=scenario_par_culture["tomate"].id or "tomate-scenario",
                               culture="tomate", hectares_alloues=3.0)
        )
    if "pomme_de_terre" in scenario_par_culture:
        allocations.append(
            AllocationChoisie(scenario_id=scenario_par_culture["pomme_de_terre"].id or "pdt-scenario",
                               culture="pomme_de_terre", hectares_alloues=3.0)
        )

    decision_request = FarmerDecisionRequest(
        terrain_id=MOCK_TERRAIN_ID,
        allocations=allocations,
        superficie_disponible_ha=MOCK_TERRAIN_SUPERFICIE_HA,
    )
    print(f"  Le farmer alloue : {[(a.culture, a.hectares_alloues) for a in allocations]}")

    print("\n" + "=" * 70)
    print("ÉTAPE E — Rapport final (coût final + dates de maturité pour l'agent Monitoring)")
    print("=" * 70)
    decision_response = confirmer_decision(decision_request)
    print(json.dumps(decision_response.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
