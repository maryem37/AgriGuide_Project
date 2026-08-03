/**
 * Client API pour l'agent Business (backend/agent_business).
 *
 * Les types ci-dessous reflètent volontairement, champ à champ,
 * `backend/agent_business/app/models/schemas.py` pour éviter tout mapping
 * caché entre les deux couches.
 *
 * URL du service : `VITE_AGENT_BUSINESS_URL` (défaut : http://localhost:8000,
 * cf. `backend/agent_business/README.md` — `uvicorn app.main:app --reload`).
 */

const BUSINESS_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_BUSINESS_URL as string | undefined) ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Entrée — reflète CropRecommendation / BusinessAdvisorRequest
// ---------------------------------------------------------------------------

export type CropRecommendation = {
  rang: number;
  culture: string;
  score_compatibilite: number;
  cycle_jours: number;
  besoins_irrigation: Record<string, unknown>;
  besoins_engrais: Record<string, unknown>;
  besoins_pesticides: Record<string, unknown>;
  feature_importance: Record<string, unknown>;
};

export type BusinessAdvisorRequest = {
  terrain_id: string;
  superficie_disponible_ha: number;
  budget_input: number;
  date_plantation_prevue: string; // ISO date (YYYY-MM-DD)
  crop_recommendations: CropRecommendation[];
  nb_scenarios?: number;
};

// ---------------------------------------------------------------------------
// Sortie — reflète EtudeMarche / BusinessScenario / BusinessAdvisorResponse
// ---------------------------------------------------------------------------

export type EtudeMarche = {
  prix_moyen_eur_par_kg: number;
  rendement_estime_kg_par_ha: number;
  tendance_prix: number;
  date_recolte_estimee: string;
  profit_brut_par_ha: number;
  source: string;
  /** Variation d'indice Agreste IPPAP sur ~6 mois (%) */
  indice_pct_change?: number | null;
  latest_index?: number | null;
  produit_agreste?: string | null;
  justification_marche?: string | null;
  market_score?: number | null;
  tendance_label?: string | null;
  demande?: string | null;
  concurrence?: string | null;
};

/** Explique comment une métrique a été calculée : formule, valeurs intermédiaires, sources. */
export type DetailCalculMetrique = {
  formule: string;
  valeurs: Record<string, unknown>;
  sources: string[];
};

export type DetailCalculScenario = {
  score_matching: DetailCalculMetrique;
  surface_conseillee: DetailCalculMetrique;
  rendement_estime: DetailCalculMetrique;
  recolte_estimee: DetailCalculMetrique;
  profit_estime: DetailCalculMetrique;
};

export type BusinessScenario = {
  id: string | null;
  terrain_id: string;
  budget_input: number;
  culture: string;
  quantite_par_ha: number;
  profit_estime: number;
  risque_score: number; // 0 à 1
  risque_description: string;
  solution_risque: string;
  matching_score: number; // 0 à 100
  etude_marche: EtudeMarche;
  superficie_max_financable_ha: number;
  superficie_conseillee_ha: number;
  detail_calcul: DetailCalculScenario;
  created_at: string;
};

export type BusinessAdvisorResponse = {
  terrain_id: string;
  budget_input: number;
  scenarios: BusinessScenario[];
};

// ---------------------------------------------------------------------------
// Human-in-the-loop — reflète AllocationChoisie / FarmerDecisionRequest/Response
// ---------------------------------------------------------------------------

export type AllocationChoisie = {
  scenario_id: string;
  culture: string;
  hectares_alloues: number;
};

export type FarmerDecisionRequest = {
  terrain_id: string;
  allocations: AllocationChoisie[];
  superficie_disponible_ha: number;
};

export type DecisionAllocationDetaillee = {
  scenario_id: string;
  culture: string;
  hectares_alloues: number;
  cout_alloue: number;
  date_maturite_prevue: string;
};

export type FarmerDecisionResponse = {
  decision_id: string;
  terrain_id: string;
  statut: string;
  cout_final: number;
  superficie_totale_allouee_ha: number;
  allocations: DecisionAllocationDetaillee[];
  created_at: string;
};

export class BusinessApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "BusinessApiError";
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${BUSINESS_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new BusinessApiError(
      `Impossible de joindre l'agent Business (${BUSINESS_API_BASE_URL}). Vérifiez qu'il tourne (uvicorn app.main:app --reload).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new BusinessApiError(
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} de l'agent Business`),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

/** POST /business/scenarios — génère les N scénarios chiffrés pour ce budget/terrain. */
export function fetchBusinessScenarios(
  request: BusinessAdvisorRequest,
): Promise<BusinessAdvisorResponse> {
  return postJson<BusinessAdvisorResponse>("/business/scenarios", {
    nb_scenarios: 3,
    ...request,
  });
}

/** POST /business/decision — confirme la répartition finale choisie par le farmer. */
export function confirmFarmerDecision(
  request: FarmerDecisionRequest,
): Promise<FarmerDecisionResponse> {
  return postJson<FarmerDecisionResponse>("/business/decision", request);
}
