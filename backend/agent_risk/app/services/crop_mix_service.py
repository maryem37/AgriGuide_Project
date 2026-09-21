"""
Service d'optimisation d'asassolement (Crop Mix Optimization).

Utilise la programmation linéaire (scipy.optimize.linprog / HiGHS solver) pour déterminer
la répartition optimale d'hectares par culture afin de maximiser le profit net global
de l'exploitation agricole sous contraintes de surface, budget et plafonnement anti-monoculture.
"""

from __future__ import annotations
from datetime import date
import numpy as np
from scipy.optimize import linprog

from app.models.schemas import (
    CropAllocation,
    CropMixRequest,
    CropMixResponse,
)

METHODOLOGY_DISCLAIMER = (
    "Note V1 (Business Heuristic Score) : Optimisation d'asassolement par programmation linéaire (scipy.optimize.linprog / HiGHS) "
    "maximisant le profit net global sous contraintes de surface totale, budget disponible "
    "et plafonnement anti-monoculture (max 50% de la surface par culture). "
    "L'indice Herfindahl-Hirschman (HHI) est un proxy d'orientation produit d'ingénierie interne (sans lien avec la modélisation publiée de Belhsen et al. 2026). "
    "Les contraintes de rotation pluriannuelle et les variances financières sont prévues pour la V2."
)

DEFAULT_CROP_COSTS = {
    "ble_tendre": 1050.0,
    "mais": 1235.0,
    "colza": 1150.0,
    "orge": 950.0,
    "tournesol": 850.0,
    "default": 1000.0,
}

DEFAULT_CROP_PROFITS = {
    "ble_tendre": 690.0,
    "mais": 558.0,
    "colza": 610.0,
    "orge": 480.0,
    "tournesol": 420.0,
    "default": 500.0,
}


def optimize_crop_mix(req: CropMixRequest) -> CropMixResponse:
    """Calcule la répartition optimale des hectares par culture via programmation linéaire."""
    valid_crops = [
        crop for crop in req.crop_recommendations
        if crop.score_compatibilite >= req.min_compatibility_score
    ]
    if not valid_crops:
        valid_crops = sorted(req.crop_recommendations, key=lambda c: c.score_compatibilite, reverse=True)[:1]

    n_crops = len(valid_crops)

    costs_per_ha = []
    profits_net_per_ha = []
    crop_names = []
    compat_scores = []

    for crop in valid_crops:
        crop_key = crop.culture.lower()
        cost_ha = DEFAULT_CROP_COSTS.get(crop_key, DEFAULT_CROP_COSTS["default"])
        profit_ha = DEFAULT_CROP_PROFITS.get(crop_key, DEFAULT_CROP_PROFITS["default"])

        costs_per_ha.append(cost_ha)
        profits_net_per_ha.append(profit_ha)
        crop_names.append(crop.culture)
        compat_scores.append(crop.score_compatibilite)

    c = [-p for p in profits_net_per_ha]

    A_ub = [
        [1.0] * n_crops,
        costs_per_ha,
    ]
    b_ub = [
        req.superficie_disponible_ha,
        req.budget_input,
    ]

    max_ha_per_crop = req.superficie_disponible_ha * req.max_single_crop_share
    bounds = [(0.0, max_ha_per_crop) for _ in range(n_crops)]

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

    allocations: list[CropAllocation] = []
    total_used_ha = 0.0
    total_used_budget = 0.0
    total_net_profit = 0.0

    if res.success:
        alloc_ha = [round(max(0.0, float(x)), 2) for x in res.x]
        optimization_status = "OPTIMAL"
    else:
        optimization_status = "FEASIBLE_FALLBACK"
        cheapest_idx = int(np.argmin(costs_per_ha))
        alloc_ha = [0.0] * n_crops
        max_possible_ha = min(req.superficie_disponible_ha, req.budget_input / max(1.0, costs_per_ha[cheapest_idx]))
        alloc_ha[cheapest_idx] = round(max_possible_ha, 2)

    total_used_ha = round(sum(alloc_ha), 2)
    
    for idx in range(n_crops):
        ha = alloc_ha[idx]
        if ha > 0.001:
            cost = round(ha * costs_per_ha[idx], 2)
            profit = round(ha * profits_net_per_ha[idx], 2)
            pct = round((ha / total_used_ha * 100.0) if total_used_ha > 0 else 0.0, 1)
            
            total_used_budget += cost
            total_net_profit += profit

            allocations.append(
                CropAllocation(
                    culture=crop_names[idx],
                    hectares_alloues=ha,
                    pourcentage_surface=pct,
                    profit_estime_eur=profit,
                    cout_total_eur=cost,
                    score_compatibilite=compat_scores[idx],
                )
            )

    total_used_budget = round(total_used_budget, 2)
    total_net_profit = round(total_net_profit, 2)
    roi_global_pct = round((total_net_profit / total_used_budget * 100.0) if total_used_budget > 0 else 0.0, 1)

    if allocations and total_used_ha > 0:
        hhi_score = round(sum((alloc.pourcentage_surface) ** 2 for alloc in allocations), 1)
    else:
        hhi_score = 10000.0

    if hhi_score < 1500:
        diversification_label = "DIVERSIFIÉ"
    elif hhi_score <= 2500:
        diversification_label = "MODÉRÉ"
    else:
        diversification_label = "CONCENTRÉ"

    allocations = sorted(allocations, key=lambda a: a.hectares_alloues, reverse=True)

    return CropMixResponse(
        terrain_id=req.terrain_id,
        superficie_totale_ha=req.superficie_disponible_ha,
        superficie_utilisee_ha=total_used_ha,
        budget_total_eur=req.budget_input,
        budget_utilise_eur=total_used_budget,
        profit_total_estime_eur=total_net_profit,
        roi_global_pct=roi_global_pct,
        diversification_hhi_score=hhi_score,
        diversification_label=diversification_label,
        optimization_status=optimization_status,
        allocations=allocations,
        methodology_note=METHODOLOGY_DISCLAIMER,
    )
