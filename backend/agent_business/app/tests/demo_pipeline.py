"""
Démo bout-en-bout de l'agent Business, sans serveur FastAPI, pour valider
toute la chaîne : données simulées -> scénarios -> décision du farmer ->
rapport final.

Exécution : python -m app.tests.demo_pipeline (depuis backend/agent_business/)
"""

import json
from datetime import date

from app.models.schemas import (
    BusinessAdvisorRequest,
    CropRecommendation,
    FarmerDecisionRequest,
    AllocationChoisie,
)
from app.services.scenario_generator import generer_scenarios
from app.services.decision_service import confirmer_decision
from app.services.persistence_service import save_scenarios

TERRAIN_ID = "11111111-1111-1111-1111-111111111111"
TERRAIN_SUPERFICIE_HA = 12.0
DATE_PLANTATION = date(2026, 3, 15)


def agriculture_recommendations() -> list[dict]:
    return [
        {
            "rang": rank,
            "culture": culture,
            "score_compatibilite": compatibility,
            "cycle_jours": cycle,
            "besoins_irrigation": {"irrigation_need_mm": irrigation},
            "besoins_engrais": {"n_dose_kg_ha": nitrogen},
            "besoins_pesticides": {"traitements_par_saison": treatments},
            "feature_importance": {},
        }
        for rank, culture, compatibility, cycle, irrigation, nitrogen, treatments in [
            (1, "ble", 92, 240, 80, 160, 2),
            (2, "mais", 84, 150, 160, 190, 2),
            (3, "tournesol", 76, 130, 40, 60, 1),
        ]
    ]


def run_demo():
    print("=" * 70)
    print("ÉTAPE A — Chargement des données simulées (crop_recommendations)")
    print("=" * 70)
    crops_raw = agriculture_recommendations()
    crops = [CropRecommendation(**c) for c in crops_raw]
    for c in crops:
        print(f"  - {c.culture} (score agri: {c.score_compatibilite}, cycle: {c.cycle_jours}j)")

    print("\n" + "=" * 70)
    print("ÉTAPE B — Requête Business Advisor (budget du farmer)")
    print("=" * 70)
    budget_farmer = 25000.0  # exemple : 25 000 EUR de budget disponible
    request = BusinessAdvisorRequest(
        terrain_id=TERRAIN_ID,
        superficie_disponible_ha=TERRAIN_SUPERFICIE_HA,
        budget_input=budget_farmer,
        date_plantation_prevue=DATE_PLANTATION,
        crop_recommendations=crops,
        nb_scenarios=3,
    )
    print(f"  Budget : {budget_farmer} EUR | Superficie disponible : {TERRAIN_SUPERFICIE_HA} ha")

    print("\n" + "=" * 70)
    print("ÉTAPE C — Génération des 3 scénarios (market study + risk study + scoring)")
    print("=" * 70)
    scenarios = generer_scenarios(request)
    save_scenarios(scenarios)
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
    # Exemple : le farmer confirme 1 ha du scénario le mieux classé.
    selected = scenarios[0]
    allocations = [
        AllocationChoisie(
            scenario_id=selected.id,
            culture=selected.culture,
            hectares_alloues=min(1.0, selected.superficie_conseillee_ha),
        )
    ]

    decision_request = FarmerDecisionRequest(
        terrain_id=TERRAIN_ID,
        allocations=allocations,
        superficie_disponible_ha=TERRAIN_SUPERFICIE_HA,
    )
    print(f"  Le farmer alloue : {[(a.culture, a.hectares_alloues) for a in allocations]}")

    print("\n" + "=" * 70)
    print("ÉTAPE E — Rapport final (coût final + dates de maturité pour l'agent Monitoring)")
    print("=" * 70)
    decision_response = confirmer_decision(decision_request)
    print(json.dumps(decision_response.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
