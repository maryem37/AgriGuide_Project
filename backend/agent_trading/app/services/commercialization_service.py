"""
Commercialization Strategy Service (SELL / HOLD / STORE / HEDGE).
"""
from __future__ import annotations

from app.models.schemas import (
    StrategyEvaluationRequest,
    StrategyDecisionResponse,
    MarketFeedItem,
)
from app.services.market_ticker_service import COMMODITIES_DB, get_live_quote, require_execution_eligible_data

def calculate_strategy(req: StrategyEvaluationRequest) -> StrategyDecisionResponse:
    """Evaluate the farmer's position and recommend the best commercial action dynamically."""
    require_execution_eligible_data()
    symbol = (req.commodity_symbol or "EBM").upper()
    if symbol not in COMMODITIES_DB:
        symbol = "EBM"
    meta = COMMODITIES_DB[symbol]
    market_price = get_live_quote(symbol)["price_eur_ton"]
    
    uncommitted = max(0, req.total_harvest_tons - req.already_committed_tons)
    break_even = max(1.0, req.break_even_cost_eur_ton or 180.0)
    margin_pct = req.target_margin_pct if req.target_margin_pct is not None else 20.0
    target_price = round(break_even * (1.0 + margin_pct / 100.0), 2)
    
    current_margin_eur = round(market_price - break_even, 2)
    current_margin_pct = round((current_margin_eur / break_even) * 100.0, 1)
    price_gap_eur = round(target_price - market_price, 2)
    
    storage_cap = req.storage_capacity_tons or 0
    storage_deficit = max(0, uncommitted - storage_cap)
    
    snapshot = [
        MarketFeedItem(
            source="market_provider",
            label=f"Futures Euronext ({meta['name']})",
            commodity=meta["name"],
            price_eur_ton=market_price,
            change_pct=1.2,
            contract_or_location="Échéance Proche",
            updated_at="Live"
        )
    ]
    
    signals = {
        "rsi": "52 (Zone Neutre Favorable)",
        "trend": "Haussière Moderée",
        "price_vs_target": f"{market_price} €/t vs cible {target_price} €/t (Écart : {price_gap_eur} €/t)"
    }

    # Case 1: All harvest already committed
    if uncommitted <= 0:
        return _build_response(
            "HOLD", "MAINTENIR POSITION", 95,
            "Récolte 100% Sous Contrat",
            [
                f"L'intégralité de votre récolte de {req.total_harvest_tons} t est déjà vendue ou engagée sous contrat.",
                "Aucun risque de baisse du marché sur ce volume."
            ],
            signals, 0, market_price, 0, "low", None,
            [
                f"1. Vérifier le calendrier de livraison de vos {req.already_committed_tons} t avec votre acheteur.",
                "2. Surveiller la bonne exécution logistique."
            ],
            snapshot
        )

    # Case 2: Market price >= Target price
    if market_price >= target_price:
        rec_vol = round(uncommitted * 0.6, 1)
        gain = round(rec_vol * current_margin_eur, 2)
        return _build_response(
            "SELL", "VENTE RECOMMANDÉE (OBJECTIF ATTEINT)", 88,
            f"Le prix du marché ({market_price} €/t) dépasse votre objectif ({target_price} €/t) !",
            [
                f"Votre coût de revient ({break_even} €/t) + marge visée ({margin_pct}%) est atteint à {target_price} €/t.",
                f"En vendant {rec_vol} t maintenant, vous réalisez une marge nette instantanée de +{current_margin_eur} €/t (+{gain:,.0f} € au total).",
                f"Capacité de stockage disponible ({storage_cap} t) : Sécuriser {rec_vol} t libère la trésorerie sans engorger les hangars."
            ],
            signals, rec_vol, market_price, gain, "low", None,
            [
                f"1. Valider la vente de {rec_vol} t auprès de votre coopérative au cours de {market_price} €/t.",
                f"2. Conserver le solde de {round(uncommitted - rec_vol, 1)} t en option haussière.",
                f"3. Placer un ordre limite de protection au prix de {target_price} €/t."
            ],
            snapshot
        )

    # Case 3: Market price < Target price BUT current margin is positive (>0)
    if current_margin_eur > 0:
        if storage_deficit > 0:
            # Storage is limited (cannot store full uncommitted volume)
            rec_vol = min(uncommitted, max(50.0, round(storage_deficit * 0.5, 1)))
            gain = round(rec_vol * current_margin_eur, 2)
            storage_info = {
                "capacity_tons": storage_cap,
                "deficit_tons": storage_deficit,
                "cost_note": f"Déficit de stockage de {storage_deficit} t — Risque de frais de gardiennage."
            }
            return _build_response(
                "HEDGE", "VENTE PARTIELLE & STOCKAGE SELECTIF", 84,
                f"Prix à {market_price} €/t (Marge actuelle +{current_margin_eur} €/t soit {current_margin_pct}%) — Stockage limité ({storage_cap} t sur {uncommitted} t).",
                [
                    f"Le prix actuel ({market_price} €/t) est sous votre cible de {target_price} €/t, mais génère tout de même +{current_margin_eur} €/t de marge positive.",
                    f"Déficit de stockage de {storage_deficit} t : Votre capacité au hangar ({storage_cap} t) ne couvre pas vos {uncommitted} t restantes.",
                    f"Engager une tranche de {rec_vol} t à {market_price} €/t évite les pénalités de stockage extérieur tout en dégageant +{gain:,.0f} € de trésorerie."
                ],
                signals, rec_vol, market_price, gain, "medium", storage_info,
                [
                    f"1. Vendre immédiatement {rec_vol} t à {market_price} €/t pour résorber le manque de stockage.",
                    f"2. Placer vos {min(storage_cap, uncommitted)} t sous hangar à l'abri de l'humidité.",
                    f"3. Déposer un ordre limite à {target_price} €/t pour les {round(uncommitted - rec_vol - min(storage_cap, uncommitted), 1)} t restantes."
                ],
                snapshot
            )

        # Full storage capacity available
        storage_info = {
            "capacity_tons": storage_cap,
            "cost_per_month": 1.5,
            "max_duration_months": 5
        }
        return _build_response(
            "STORE", "STOCKER & ATTENDRE L'OBJECTIF", 82,
            f"Prix à {market_price} €/t sous l'objectif de {target_price} €/t — Stockage suffisant ({storage_cap} t disponibles).",
            [
                f"Le prix du marché ({market_price} €/t) manque encore de {price_gap_eur} €/t pour atteindre votre cible de {target_price} €/t ({margin_pct}% de marge).",
                f"Votre capacité de stockage au hangar ({storage_cap} t) couvre l'intégralité de vos {uncommitted} t restantes.",
                "Le report de vente sur 2 à 4 mois permet d'attendre un rebond de marché sans subir de frais extérieurs."
            ],
            signals, 0, target_price, 0, "medium", storage_info,
            [
                f"1. Mettre vos {uncommitted} t sous ventilation au hangar.",
                f"2. Déposer un ordre à cours limité de {target_price} €/t auprès de votre organisme stockeur.",
                "3. Suivre les alertes de volatilité Euronext hebdomadaires sur AgriGuide."
            ],
            snapshot
        )

    # Case 4: Market price <= Break even cost (Negative margin)
    rec_vol = min(uncommitted, 50.0)
    return _build_response(
        "HOLD", "PATIENTER (MARGE EN DANGER)", 75,
        f"Prix du marché ({market_price} €/t) sous votre coût de revient ({break_even} €/t) !",
        [
            f"Une vente immédiate à {market_price} €/t génèrerait une perte de {abs(current_margin_eur)} €/t.",
            f"Votre prix visé est de {target_price} €/t (écart de {price_gap_eur} €/t).",
            "Conservez vos volumes et attendez le redressement des cours."
        ],
        signals, 0, target_price, 0, "high", None,
        [
            "1. Stopper toute nouvelle vente ferme à ce niveau de cours.",
            f"2. Fixer un ordre d'alerte dès que le marché repasse au-dessus de {break_even} €/t.",
            "3. Contacter votre conseiller agronomique pour étudier les options de stockage prolongé."
        ],
        snapshot
    )


def _build_response(
    action, action_label, conf, head, rationale, signals, rec_vol, rec_price, gain, risk, storage, plan, snapshot
) -> StrategyDecisionResponse:
    return StrategyDecisionResponse(
        action=action,
        action_label=action_label,
        confidence_score_pct=conf,
        headline=head,
        rationale=rationale,
        market_signals=signals,
        recommended_volume_tons=rec_vol,
        recommended_target_price_eur_ton=rec_price,
        estimated_total_gain_eur=gain,
        risk_level=risk,
        storage_analysis=storage,
        step_by_step_plan=plan,
        tri_source_snapshot=snapshot
    )

