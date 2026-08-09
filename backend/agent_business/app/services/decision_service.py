"""
Service Decision — traite la confirmation du farmer (human-in-the-loop).

Valide que la somme des hectares alloués ne dépasse pas la superficie
disponible, calcule le coût final réel, et déduit la date de maturité
prévue par culture (champ clé réutilisé plus tard par l'agent Monitoring
pour déclencher la suggestion de dépôt marketplace).
"""

import uuid

from app.models.schemas import FarmerDecisionRequest, FarmerDecisionResponse
from app.services.persistence_service import get_scenarios, save_decision


class AllocationInvalideError(Exception):
    pass


def confirmer_decision(request: FarmerDecisionRequest) -> FarmerDecisionResponse:
    total_alloue = sum(a.hectares_alloues for a in request.allocations)

    if total_alloue > request.superficie_disponible_ha:
        raise AllocationInvalideError(
            f"Le total alloué ({total_alloue} ha) dépasse la superficie "
            f"disponible ({request.superficie_disponible_ha} ha)."
        )

    scenario_ids = [allocation.scenario_id for allocation in request.allocations]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise AllocationInvalideError("Un même scénario ne peut être alloué qu'une fois.")
    scenarios = get_scenarios(scenario_ids)
    missing = [scenario_id for scenario_id in scenario_ids if scenario_id not in scenarios]
    if missing:
        raise AllocationInvalideError(
            "Scénario inconnu ou expiré: " + ", ".join(missing)
        )

    cout_final = 0.0
    allocations_detaillees = []

    for allocation in request.allocations:
        scenario = scenarios[allocation.scenario_id]
        if scenario.terrain_id != request.terrain_id:
            raise AllocationInvalideError("Le scénario ne correspond pas au terrain demandé.")
        if scenario.culture != allocation.culture:
            raise AllocationInvalideError("La culture ne correspond pas au scénario sélectionné.")
        if allocation.hectares_alloues > scenario.superficie_conseillee_ha:
            raise AllocationInvalideError(
                f"L'allocation de {allocation.culture} dépasse la surface conseillée "
                f"({scenario.superficie_conseillee_ha} ha)."
            )

        cout_total_ha = scenario.indicateurs_financiers.cout_total_eur_par_ha
        cout_culture = cout_total_ha * allocation.hectares_alloues
        cout_final += cout_culture

        date_maturite_prevue = scenario.etude_marche["date_recolte_estimee"]

        allocations_detaillees.append(
            {
                "scenario_id": allocation.scenario_id,
                "culture": allocation.culture,
                "hectares_alloues": allocation.hectares_alloues,
                "cout_alloue": round(cout_culture, 2),
                "date_maturite_prevue": str(date_maturite_prevue),
            }
        )

    budget = min(scenario.budget_input for scenario in scenarios.values())
    if cout_final > budget:
        raise AllocationInvalideError(
            f"Le coût final ({cout_final:.2f} €) dépasse le budget ({budget:.2f} €)."
        )

    response = FarmerDecisionResponse(
        decision_id=str(uuid.uuid4()),
        terrain_id=request.terrain_id,
        statut="confirmed",
        cout_final=round(cout_final, 2),
        superficie_totale_allouee_ha=total_alloue,
        allocations=allocations_detaillees,
    )
    save_decision(response)
    return response
