/**
 * Client API pour l'agent Risk Analyst (backend/agent_risk).
 *
 * Microservice dédié à l'évaluation des risques agricoles :
 * - Risque climatique paramétrique (Belhsen et al., 2026, JRACR)
 * - Optimisation d'assolement & Diversification HHI (HiGHS linprog)
 * - Génération de rapport HTML d'expertise climatique (8 sections + SVG)
 *
 * URL du service : `VITE_AGENT_RISK_URL` (défaut : http://localhost:8010,
 * cf. `backend/agent_risk/README.md` — `uvicorn app.main:app --reload --port 8010`).
 */

const RISK_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_RISK_URL as string | undefined) ?? "http://localhost:8010";

export class RiskApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "RiskApiError";
  }
}

async function postJson<TResponse>(
  path: string,
  body: unknown,
  token: string,
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${RISK_API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new RiskApiError(
      `Impossible de joindre l'agent Risk (${RISK_API_BASE_URL}). Vérifiez qu'il tourne (port 8010).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new RiskApiError(
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} de l'agent Risk`),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

// ---------------------------------------------------------------------------
// Climate Risk Types & Requests
// ---------------------------------------------------------------------------

export type ClimateRiskRequest = {
  lat: number;
  lon: number;
  crop_type?: string;
  parcel_id?: string;
  ndvi_current?: number | null;
  ndvi_max_baseline?: number;
};

export type RiskBreakdown = {
  spi_3m: number;
  spei_3m: number;
  ndvi_decay: number;
  composite_index: number;
  drought_component_score: number;
  vegetation_stress_score: number;
  formula_explanation: string;
};

export type InsuranceRecommendation = {
  suggested_coverage: string;
  estimated_annual_premium_eur_ha: number;
  payout_trigger_threshold: number;
  payout_exhaustion_threshold: number;
  reasoning: string;
};

export type ClimateRiskResponse = {
  parcel_id: string;
  crop_type: string;
  risk_score: number;
  risk_level: "FAIBLE" | "MODÉRÉ" | "ÉLEVÉ" | "CRITIQUE";
  risk_breakdown: RiskBreakdown;
  insurance_recommendation: InsuranceRecommendation;
  methodology_note: string;
};

// ---------------------------------------------------------------------------
// Crop Mix Types & Requests
// ---------------------------------------------------------------------------

export type CropRecommendationInput = {
  rang: number;
  culture: string;
  score_compatibilite: number;
  cycle_jours: number;
  besoins_irrigation: Record<string, unknown>;
  besoins_engrais: Record<string, unknown>;
  besoins_pesticides: Record<string, unknown>;
  feature_importance: Record<string, unknown>;
};

export type CropMixRequest = {
  terrain_id: string;
  superficie_disponible_ha: number;
  budget_input: number;
  crop_recommendations: CropRecommendationInput[];
  max_single_crop_share?: number;
  min_compatibility_score?: number;
};

export type CropAllocation = {
  culture: string;
  hectares_alloues: number;
  pourcentage_surface: number;
  profit_estime_eur: number;
  cout_total_eur: number;
  score_compatibilite: number;
};

export type CropMixResponse = {
  terrain_id: string;
  superficie_totale_ha: number;
  superficie_utilisee_ha: number;
  budget_total_eur: number;
  budget_utilise_eur: number;
  profit_total_estime_eur: number;
  roi_global_pct: number;
  diversification_hhi_score: number;
  diversification_label: "DIVERSIFIÉ" | "MODÉRÉ" | "CONCENTRÉ";
  optimization_status: string;
  allocations: CropAllocation[];
  methodology_note: string;
};

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/** POST /risk/climate — calcule le score de risque climatique paramétrique (Belhsen et al., 2026). */
export function fetchClimateRisk(
  request: ClimateRiskRequest,
  token: string,
): Promise<ClimateRiskResponse> {
  return postJson<ClimateRiskResponse>("/risk/climate", request, token);
}

/** POST /risk/climate/report — génère le rapport HTML autonome avec graphiques SVG. */
export async function fetchClimateRiskReportHtml(
  request: ClimateRiskRequest,
  token: string,
): Promise<string> {
  const response = await fetch(`${RISK_API_BASE_URL}/risk/climate/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new RiskApiError("Erreur lors de la génération du rapport HTML climatique", response.status);
  }
  return response.text();
}

/** POST /risk/crop-mix — calcule l'assolement optimal par programmation linéaire (HiGHS). */
export function fetchCropMix(
  request: CropMixRequest,
  token: string,
): Promise<CropMixResponse> {
  return postJson<CropMixResponse>("/risk/crop-mix", request, token);
}
