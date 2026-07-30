"""
Service Decision — traite la confirmation du farmer (human-in-the-loop).

Valide que la somme des hectares alloués ne dépasse pas la superficie
disponible, calcule le coût final réel, et déduit la date de maturité
prévue par culture (champ clé réutilisé plus tard par l'agent Monitoring
pour déclencher la suggestion de dépôt marketplace).
"""

import uuid
from datetime import date, timedelta

from app.data.mock_crop_recommendations import get_mock_crop_recommendations, MOCK_DATE_PLANTATION
from app.data.mock_production_costs import get_mock_production_cost_per_ha
from app.data.mock_risks import get_mock_crop_risk
from app.models.schemas import FarmerDecisionRequest, FarmerDecisionResponse


class AllocationInvalideError(Exception):
    pass


def confirmer_decision(request: FarmerDecisionRequest) -> FarmerDecisionResponse:
    total_alloue = sum(a.hectares_alloues for a in request.allocations)

    if total_alloue > request.superficie_disponible_ha:
        raise AllocationInvalideError(
            f"Le total alloué ({total_alloue} ha) dépasse la superficie "
            f"disponible ({request.superficie_disponible_ha} ha)."
        )

    # Table de correspondance culture -> cycle_jours (vient normalement de
    # crop_recommendations déjà chargées en amont ; on la relit ici en mock)
    cycles_par_culture = {c["culture"]: c["cycle_jours"] for c in get_mock_crop_recommendations()}

    cout_final = 0.0
    allocations_detaillees = []

    for allocation in request.allocations:
        cout_production_ha = get_mock_production_cost_per_ha(allocation.culture)
        risque = get_mock_crop_risk(allocation.culture)
        cout_total_ha = cout_production_ha + risque["cout_mitigation_eur_par_ha"]
        cout_culture = cout_total_ha * allocation.hectares_alloues
        cout_final += cout_culture

        cycle_jours = cycles_par_culture.get(allocation.culture, 90)
        date_maturite_prevue = MOCK_DATE_PLANTATION + timedelta(days=cycle_jours)

        allocations_detaillees.append(
            {
                "scenario_id": allocation.scenario_id,
                "culture": allocation.culture,
                "hectares_alloues": allocation.hectares_alloues,
                "cout_alloue": round(cout_culture, 2),
                "date_maturite_prevue": date_maturite_prevue.isoformat(),
            }
        )

    return FarmerDecisionResponse(
        decision_id=str(uuid.uuid4()),
        terrain_id=request.terrain_id,
        statut="confirmed",
        cout_final=round(cout_final, 2),
        superficie_totale_allouee_ha=total_alloue,
        allocations=allocations_detaillees,
    )
