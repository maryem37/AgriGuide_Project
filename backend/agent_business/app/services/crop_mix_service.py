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
from app.services.financial_service import estimate_production_cost
from app.services.market_study import estimer_marche
from app.services.risk_study import evaluer_risque

METHODOLOGY_DISCLAIMER = (
    "Note V1 (Business Heuristic Score) : Optimisation d'asassolement par programmation linéaire (scipy.optimize.linprog / HiGHS) "
    "maximisant le profit net global sous contraintes de surface totale, budget disponible "
    "et plafonnement anti-monoculture (max 50% de la surface par culture). "
    "L'indice Herfindahl-Hirschman (HHI) est un proxy d'orientation produit d'ingénierie interne (sans lien avec la modélisation publiée de Belhsen et al. 2026). "
    "Les contraintes de rotation pluriannuelle et les variances financières sont prévues pour la V2."
)


def optimize_crop_mix(req: CropMixRequest) -> CropMixResponse:
    """Calcule la répartition optimale des hectares par culture via programmation linéaire."""
    
    # 1. Filtrer les cultures éligibles (score compatibilité agronomique >= min_compatibility_score)
    valid_crops = [
        crop for crop in req.crop_recommendations
        if crop.score_compatibilite >= req.min_compatibility_score
    ]
    if not valid_crops:
        # Fallback si aucune culture ne dépasse le seuil minimum
        valid_crops = sorted(req.crop_recommendations, key=lambda c: c.score_compatibilite, reverse=True)[:1]

    today = date.today()
    n_crops = len(valid_crops)

    costs_per_ha = []
    profits_net_per_ha = []
    crop_names = []
    compat_scores = []

    for crop in valid_crops:
        etude_marche = estimer_marche(crop, today)
        cout_estime = estimate_production_cost(crop)
        etude_risque = evaluer_risque(crop, etude_marche, cout_estime)

        cout_total_par_ha = cout_estime.cost_per_ha + etude_risque.cout_mitigation_eur_par_ha
        profit_net_par_ha = etude_marche.profit_brut_par_ha - cout_total_par_ha

        costs_per_ha.append(cout_total_par_ha)
        profits_net_per_ha.append(profit_net_par_ha)
        crop_names.append(crop.culture)
        compat_scores.append(crop.score_compatibilite)

    # 2. Formuler le problème de programmation linéaire pour linprog
    # linprog minimise c^T * x ==> c = -profits_net_per_ha
    c = [-p for p in profits_net_per_ha]

    # Contrainte A_ub * x <= b_ub
    # Ligne 1 : Surface totale <= superficie_disponible_ha (sum x_i <= H_total)
    # Ligne 2 : Budget total <= budget_input (sum C_i * x_i <= B_total)
    A_ub = [
        [1.0] * n_crops,
        costs_per_ha,
    ]
    b_ub = [
        req.superficie_disponible_ha,
        req.budget_input,
    ]

    # Plafond anti-monoculture par culture : 0 <= x_i <= max_single_crop_share * H_total
    max_ha_per_crop = req.superficie_disponible_ha * req.max_single_crop_share
    bounds = [(0.0, max_ha_per_crop) for _ in range(n_crops)]

    # 3. Résolution avec le solveur HiGHS
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

    allocations: list[CropAllocation] = []
    total_used_ha = 0.0
    total_used_budget = 0.0
    total_net_profit = 0.0

    if res.success:
        alloc_ha = [round(max(0.0, float(x)), 2) for x in res.x]
        optimization_status = "OPTIMAL"
    else:
        # Fallback de secours si linprog ne trouve pas de solution (ex: budget trop faible)
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

    # 4. Calcul de l'indice de diversification Herfindahl-Hirschman (HHI)
    # HHI = sum((pct_i)^2). Range: [10000/N, 10000]
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

    # Trier les allocations par surface décroissante
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
