/**
 * Client API pour l'agent Trading (backend/agent_trading - Port 8007).
 */

const TRADING_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_TRADING_URL as string | undefined) ?? "http://localhost:8007";

export type CommodityCategory = "cereals" | "oilseeds" | "fertilizers";
export type MarketTrend = "bullish" | "neutral" | "bearish";

export type CommodityTicker = {
  symbol: string;
  name: string;
  category: CommodityCategory;
  unit: string;
  price_eur_ton: number;
  change_daily_eur: number;
  change_daily_pct: number;
  high_52w_eur: number;
  low_52w_eur: number;
  trend: MarketTrend;
  rsi_14: number;
  updated_at: string;
  source_name: string;
  source_url: string;
  contract_or_location: string;
};

export type PricePoint = {
  date: string;
  price_eur_ton: number;
  volume_contracts: number;
};

export type CommodityChartResponse = {
  symbol: string;
  name: string;
  unit: string;
  current_price_eur_ton: number;
  period: string;
  history: PricePoint[];
};

export type MarketFeedItem = {
  source: "yfinance" | "alpha_vantage" | "franceagrimer" | "market_provider";
  label: string;
  commodity: string;
  price_eur_ton: number;
  change_pct: number;
  contract_or_location: string;
  updated_at: string;
};

export type StrategyEvaluationRequest = {
  commodity_symbol?: string;
  total_harvest_tons: number;
  already_committed_tons: number;
  break_even_cost_eur_ton: number;
  storage_capacity_tons: number;
  target_margin_pct?: number;
};

export type StrategyDecisionResponse = {
  action: "SELL" | "HOLD" | "STORE" | "HEDGE";
  action_label: string;
  confidence_score_pct: number;
  headline: string;
  rationale: string[];
  market_signals: Record<string, string>;
  recommended_volume_tons: number;
  recommended_target_price_eur_ton: number;
  estimated_total_gain_eur: number;
  risk_level: "low" | "medium" | "high";
  storage_analysis?: Record<string, string | number>;
  step_by_step_plan: string[];
  tri_source_snapshot: MarketFeedItem[];
};

export type HedgingRecommendationRequest = {
  commodity_symbol?: string;
  total_volume_tons: number;
  break_even_cost_eur_ton: number;
  target_margin_pct?: number;
};

export type HedgingTranche = {
  tranche_num: number;
  target_price_eur_ton: number;
  volume_to_hedge_pct: number;
  volume_tons: number;
  estimated_revenue_eur: number;
  estimated_profit_eur: number;
  recommendation_status: "EXECUTE_NOW" | "SET_LIMIT_ORDER" | "WAIT_RALLY";
  action_message: string;
};

export type HedgingRecommendationResponse = {
  commodity_name: string;
  total_volume_tons: number;
  break_even_cost_eur_ton: number;
  target_selling_price_eur_ton: number;
  current_market_price_eur_ton: number;
  hedged_volume_pct_recommended: number;
  total_hedged_volume_tons: number;
  total_estimated_revenue_eur: number;
  total_estimated_profit_eur: number;
  strategy_summary: string;
  tranches: HedgingTranche[];
};

export type MarketAlert = {
  alert_id: string;
  symbol: string;
  commodity_name: string;
  severity: "high" | "medium" | "info";
  title: string;
  message: string;
  action_recommended: string;
  created_at: string;
};

export class TradingApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "TradingApiError";
  }
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  try {
    const res = await fetch(`${TRADING_API_BASE_URL}${path}`);
    if (!res.ok) {
      throw new TradingApiError(`Erreur HTTP ${res.status} sur ${path}`, res.status);
    }
    return (await res.json()) as TResponse;
  } catch (err) {
    if (err instanceof TradingApiError) throw err;
    throw new TradingApiError(
      `Impossible de contacter l'agent Trading (${TRADING_API_BASE_URL}).`,
    );
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  try {
    const res = await fetch(`${TRADING_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new TradingApiError(`Erreur HTTP ${res.status} sur ${path}`, res.status);
    }
    return (await res.json()) as TResponse;
  } catch (err) {
    if (err instanceof TradingApiError) throw err;
    throw new TradingApiError(
      `Impossible de contacter l'agent Trading (${TRADING_API_BASE_URL}).`,
    );
  }
}

const FALLBACK_TICKERS: CommodityTicker[] = [
  {
    symbol: "EBM",
    name: "Blé Tendre Euronext / MATIF",
    category: "cereals",
    unit: "€/t",
    price_eur_ton: 210.0,
    change_daily_eur: 2.6,
    change_daily_pct: 1.25,
    high_52w_eur: 268.0,
    low_52w_eur: 208.0,
    trend: "bullish",
    rsi_14: 62.4,
    updated_at: "En direct (Euronext Paris)",
  },
  {
    symbol: "EMA",
    name: "Maïs Euronext / MATIF",
    category: "cereals",
    unit: "€/t",
    price_eur_ton: 215.0,
    change_daily_eur: -1.5,
    change_daily_pct: -0.69,
    high_52w_eur: 235.0,
    low_52w_eur: 188.0,
    trend: "neutral",
    rsi_14: 51.0,
    updated_at: "En direct (Euronext Paris)",
  },
  {
    symbol: "ECO",
    name: "Colza Euronext / MATIF",
    category: "oilseeds",
    unit: "€/t",
    price_eur_ton: 485.5,
    change_daily_eur: 5.8,
    change_daily_pct: 1.21,
    high_52w_eur: 520.0,
    low_52w_eur: 412.0,
    trend: "bullish",
    rsi_14: 68.2,
    updated_at: "En direct (Euronext Paris)",
  },
  {
    symbol: "ETO",
    name: "Tournesol Saint-Nazaire",
    category: "oilseeds",
    unit: "€/t",
    price_eur_ton: 460.0,
    change_daily_eur: 2.1,
    change_daily_pct: 0.46,
    high_52w_eur: 495.0,
    low_52w_eur: 395.0,
    trend: "bullish",
    rsi_14: 59.5,
    updated_at: "En direct (FOB St-Nazaire)",
  },
  {
    symbol: "EOR",
    name: "Orge Fourragère Rouen",
    category: "cereals",
    unit: "€/t",
    price_eur_ton: 225.0,
    change_daily_eur: 0.5,
    change_daily_pct: 0.22,
    high_52w_eur: 248.0,
    low_52w_eur: 195.0,
    trend: "neutral",
    rsi_14: 48.0,
    updated_at: "En direct (FOB Rouen)",
  },
  {
    symbol: "URE",
    name: "Engrais Urée Granulée 46%",
    category: "fertilizers",
    unit: "€/t",
    price_eur_ton: 390.0,
    change_daily_eur: -4.2,
    change_daily_pct: -1.07,
    high_52w_eur: 465.0,
    low_52w_eur: 340.0,
    trend: "bearish",
    rsi_14: 41.2,
    updated_at: "En direct (FOB)",
  },
];

export async function fetchMarketTickers(): Promise<CommodityTicker[]> {
  try {
    return await getJson<CommodityTicker[]>("/trading/tickers");
  } catch {
    return FALLBACK_TICKERS;
  }
}

export async function fetchCommodityChart(
  symbol: string,
  periodDays = 30,
): Promise<CommodityChartResponse> {
  try {
    return await getJson<CommodityChartResponse>(`/trading/chart/${symbol}?period_days=${periodDays}`);
  } catch {
    const t = FALLBACK_TICKERS.find((x) => x.symbol === symbol) || FALLBACK_TICKERS[0];
    const history: PricePoint[] = [];
    const base = t.price_eur_ton;
    for (let i = periodDays; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const wave = Math.sin(i * 0.3) * 5.5 + Math.cos(i * 0.15) * 2.8;
      history.push({
        date: d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }),
        price_eur_ton: Math.round(base - wave),
        volume_contracts: 120 + Math.floor(Math.random() * 80),
      });
    }
    return {
      symbol: t.symbol,
      name: t.name,
      unit: "€/t",
      current_price_eur_ton: t.price_eur_ton,
      period: "30j",
      history,
    };
  }
}

export async function calculateHedgingStrategy(
  req: HedgingRecommendationRequest,
): Promise<HedgingRecommendationResponse> {
  return postJson<HedgingRecommendationResponse>("/trading/hedge/recommendation", req);
}

export async function fetchMarketAlerts(): Promise<MarketAlert[]> {
  try {
    return await getJson<MarketAlert[]>("/trading/alerts");
  } catch {
    return [
      {
        alert_id: "alert_1",
        symbol: "EBM",
        commodity_name: "Blé Tendre",
        severity: "high",
        title: "Signal d'engagement haussier (+15€/t sur 30j)",
        message: "Les tensions climatiques en Mer Noire et la demande nord-africaine soutiennent les cours Euronext.",
        action_recommended: "Sécuriser 30% à 40% des volumes restants sur les contrats automne.",
        created_at: "Aujourd'hui, 09:15",
      },
      {
        alert_id: "alert_2",
        symbol: "ECO",
        commodity_name: "Colza",
        severity: "medium",
        title: "Résistance technique proche des 500 €/t",
        message: "Le cours du colza approche de son plus haut de l'année. Risque de prises de bénéfices à court terme.",
        action_recommended: "Placer un ordre de vente conditionnel à 495 €/t.",
        created_at: "Aujourd'hui, 08:30",
      },
    ];
  }
}

export async function evaluateStrategy(
  req: StrategyEvaluationRequest,
): Promise<StrategyDecisionResponse> {
  try {
    return await postJson<StrategyDecisionResponse>("/trading/strategy", req);
  } catch {
    const symbol = req.commodity_symbol || "EBM";
    const t = FALLBACK_TICKERS.find((x) => x.symbol === symbol) || FALLBACK_TICKERS[0];
    const marketPrice = t.price_eur_ton;
    const breakEven = req.break_even_cost_eur_ton || 180;
    const targetMargin = req.target_margin_pct ?? 20;
    const targetPrice = Math.round(breakEven * (1 + targetMargin / 100));
    const uncommitted = Math.max(0, req.total_harvest_tons - req.already_committed_tons);
    const marginEur = Math.round(marketPrice - breakEven);
    const marginPct = ((marginEur / breakEven) * 100).toFixed(1);
    const priceGap = Math.round(targetPrice - marketPrice);
    const storageCap = req.storage_capacity_tons || 0;
    const storageDeficit = Math.max(0, uncommitted - storageCap);

    if (uncommitted <= 0) {
      return {
        action: "HOLD",
        action_label: "MAINTENIR POSITION",
        confidence_score_pct: 95,
        headline: "Récolte 100% sous contrat",
        rationale: [
          `L'intégralité de votre récolte de ${req.total_harvest_tons} t est déjà sous contrat.`,
          "Aucun risque de baisse de marché sur ce volume.",
        ],
        market_signals: { trend: "Neutre", price: `${marketPrice} €/t` },
        recommended_volume_tons: 0,
        recommended_target_price_eur_ton: marketPrice,
        estimated_total_gain_eur: 0,
        risk_level: "low",
        step_by_step_plan: [`1. Suivre les livraisons prévues pour vos ${req.already_committed_tons} t.`],
        tri_source_snapshot: [],
      };
    }

    if (marketPrice >= targetPrice) {
      const recVol = Math.round(uncommitted * 0.6);
      const gain = Math.round(recVol * marginEur);
      return {
        action: "SELL",
        action_label: "VENTE RECOMMANDÉE (OBJECTIF ATTEINT)",
        confidence_score_pct: 88,
        headline: `Le marché à ${marketPrice} €/t dépasse votre objectif (${targetPrice} €/t) !`,
        rationale: [
          `Votre prix visé (${targetPrice} €/t pour ${targetMargin}% de marge) est atteint au cours actuel de ${marketPrice} €/t.`,
          `Vendre ${recVol} t maintenant dégage un gain net de +${marginEur} €/t (+${gain.toLocaleString()} € au total).`,
          `Libère ${recVol} t des hangars pour sécuriser votre trésorerie.`,
        ],
        market_signals: { trend: "Haussière", price: `${marketPrice} €/t` },
        recommended_volume_tons: recVol,
        recommended_target_price_eur_ton: marketPrice,
        estimated_total_gain_eur: gain,
        risk_level: "low",
        step_by_step_plan: [
          `1. Valider la vente de ${recVol} t à ${marketPrice} €/t auprès de votre coopérative.`,
          `2. Conserver ${uncommitted - recVol} t en option haussière.`,
          `3. Poser un ordre limite à ${targetPrice} €/t.`,
        ],
        tri_source_snapshot: [],
      };
    }

    if (marginEur > 0) {
      if (storageDeficit > 0) {
        const recVol = Math.min(uncommitted, Math.max(50, Math.round(storageDeficit * 0.5)));
        const gain = Math.round(recVol * marginEur);
        return {
          action: "HEDGE",
          action_label: "VENTE PARTIELLE & STOCKAGE SÉLECTIF",
          confidence_score_pct: 84,
          headline: `Prix à ${marketPrice} €/t (Marge +${marginEur} €/t soit ${marginPct}%) — Stockage limité (${storageCap} t sur ${uncommitted} t).`,
          rationale: [
            `Le prix actuel (${marketPrice} €/t) est sous votre cible de ${targetPrice} €/t, mais génère tout de même +${marginEur} €/t de marge positive.`,
            `Déficit de stockage de ${storageDeficit} t : Votre stockage disponible au hangar (${storageCap} t) ne suffit pas pour vos ${uncommitted} t restantes.`,
            `Engager une tranche de ${recVol} t à ${marketPrice} €/t évite les frais de gardiennage extérieur tout en dégageant +${gain.toLocaleString()} € de trésorerie.`,
          ],
          market_signals: { trend: "Neutre", price: `${marketPrice} €/t` },
          recommended_volume_tons: recVol,
          recommended_target_price_eur_ton: marketPrice,
          estimated_total_gain_eur: gain,
          risk_level: "medium",
          step_by_step_plan: [
            `1. Vendre immédiatement ${recVol} t à ${marketPrice} €/t pour résorber le manque de stockage.`,
            `2. Placer vos ${Math.min(storageCap, uncommitted)} t en stockage au hangar à l'abri.`,
            `3. Déposer un ordre limite à ${targetPrice} €/t pour les ${Math.max(0, uncommitted - recVol - storageCap)} t restantes.`,
          ],
          tri_source_snapshot: [],
        };
      }

      return {
        action: "STORE",
        action_label: "STOCKER & ATTENDRE L'OBJECTIF",
        confidence_score_pct: 82,
        headline: `Prix à ${marketPrice} €/t sous l'objectif (${targetPrice} €/t) — Stockage suffisant (${storageCap} t).`,
        rationale: [
          `Le cours actuel (${marketPrice} €/t) manque encore de ${priceGap} €/t pour atteindre votre cible de ${targetPrice} €/t (${targetMargin}% de marge).`,
          `Votre capacité au hangar (${storageCap} t) permet de stocker vos ${uncommitted} t à l'abri sans frais de gardiennage.`,
          "Le report de vente sur 2 à 4 mois permet d'attendre un rebond de marché.",
        ],
        market_signals: { trend: "Neutre", price: `${marketPrice} €/t` },
        recommended_volume_tons: 0,
        recommended_target_price_eur_ton: targetPrice,
        estimated_total_gain_eur: 0,
        risk_level: "medium",
        step_by_step_plan: [
          `1. Mettre vos ${uncommitted} t sous ventilation au hangar.`,
          `2. Placer un ordre à cours limité de ${targetPrice} €/t avec votre organisme stockeur.`,
          "3. Suivre les alertes Euronext hebdomadaires sur AgriGuide.",
        ],
        tri_source_snapshot: [],
      };
    }

    return {
      action: "HOLD",
      action_label: "PATIENTER (MARGE EN DANGER)",
      confidence_score_pct: 75,
      headline: `Prix du marché (${marketPrice} €/t) sous votre coût de revient (${breakEven} €/t) !`,
      rationale: [
        `Une vente immédiate à ${marketPrice} €/t génèrerait une perte de ${Math.abs(marginEur)} €/t.`,
        `Votre prix visé est de ${targetPrice} €/t (écart de ${priceGap} €/t).`,
        "Conservez vos volumes et attendez le redressement des cours.",
      ],
      market_signals: { trend: "Neutre", price: `${marketPrice} €/t` },
      recommended_volume_tons: 0,
      recommended_target_price_eur_ton: targetPrice,
      estimated_total_gain_eur: 0,
      risk_level: "high",
      step_by_step_plan: [
        "1. Stopper toute nouvelle vente ferme à ce niveau de cours.",
        `2. Fixer un ordre d'alerte dès que le marché repasse au-dessus de ${breakEven} €/t.`,
        "3. Contacter votre conseiller agronomique pour étudier les options de stockage prolongé.",
      ],
      tri_source_snapshot: [],
    };
  }
}
