/**
 * Client API pour l'agent Agriculture (backend/agent_agriculture).
 *
 * Les types ci-dessous reflètent volontairement, champ à champ,
 * `backend/agent_agriculture/app/models/schemas.py` pour éviter tout mapping
 * caché entre les deux couches (même convention que `businessApi.ts`).
 *
 * URL du service : `VITE_AGENT_AGRICULTURE_URL` (défaut :
 * http://localhost:8002, cf. `backend/agent_agriculture/README.md` —
 * `uvicorn app.main:app --reload --port 8002`).
 */

const AGRICULTURE_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_AGRICULTURE_URL as string | undefined) ?? "http://localhost:8002";

// ---------------------------------------------------------------------------
// Types communs
// ---------------------------------------------------------------------------

export type Coordinate = { lat: number; lon: number };

export type ParcelResolution = {
  resolved: boolean;
  source: "cadastre" | "rpg" | "manual" | "unresolved";
  geometry: Record<string, unknown> | null;
  centroid: Coordinate | null;
  parcel_id: string | null;
  rpg_id_parcel: string | null;
  area_ha: number | null;
  area_m2: number | null;
  crop_declared: string | null;
  is_agricultural: boolean | null;
  agricultural_note: string | null;
  warning: string | null;
};

export type NeighborParcel = { geometry: Record<string, unknown>; crop_code: string | null };

export type NeighborCropContext = {
  neighbor_count: number;
  crop_distribution_pct: Record<string, number>;
  neighbors: NeighborParcel[];
  note: string;
};

export type SoilData = {
  source: "soilgrids" | "inrae" | "unavailable";
  ph: number | null;
  nitrogen_g_kg: number | null;
  organic_carbon_g_kg: number | null;
  sand_pct: number | null;
  clay_pct: number | null;
  silt_pct: number | null;
  cec_cmolkg: number | null;
  bulk_density_kg_dm3: number | null;
  coarse_fragments_pct: number | null;
  depth_cm: string | null;
  warning: string | null;
};

export type WeatherData = {
  source: "open-meteo" | "unavailable";
  daily_temp_mean_c: (number | null)[] | null;
  daily_precip_mm: (number | null)[] | null;
  daily_et0_mm: (number | null)[] | null;
  daily_dates: string[] | null;
  warning: string | null;
};

export type WeatherStats = {
  mean_temp_c?: number;
  min_temp_c?: number;
  max_temp_c?: number;
  total_precip_mm?: number;
  rainy_days_count?: number;
};

export type VegetationData = {
  source: "sentinel-2" | "unavailable";
  mean_ndvi: number | null;
  observation_window_days: number | null;
  valid_pixel_count: number | null;
  warning: string | null;
};

export type DLCropObservation = {
  source: "dl-tempcnn-breizhcrops" | "unavailable";
  predicted_class_fr: string | null;
  predicted_class_en: string | null;
  confidence: number | null;
  observation_timesteps: number | null;
  warning: string | null;
};

export type AgroCalcEstimate = {
  crop: string;
  n_dose_kg_ha: number | null;
  n_besoins_kg_ha: number | null;
  n_fournitures_kg_ha: number | null;
  yield_objective_q_ha: number | null;
  n_method_note: string | null;
  irrigation_need_mm: number | null;
  irrigation_window_days: number | null;
  total_et0_mm: number | null;
  total_effective_precip_mm: number | null;
  irrigation_method_note: string | null;
  warning: string | null;
};

export type AdvisorReport = {
  parcel_id: string | null;
  report_markdown: string;
  warnings: string[];
  unverified_figures: string[];
};

/** Même shape que `CropRecommendation` dans `businessApi.ts` — voir schema.sql `crop_recommendations`. */
export type CropRecommendationOut = {
  rang: number;
  culture: string;
  score_compatibilite: number;
  cycle_jours: number;
  besoins_irrigation: Record<string, unknown>;
  besoins_engrais: Record<string, unknown>;
  besoins_pesticides: Record<string, unknown>;
  feature_importance: Record<string, unknown>;
};

// ---------------------------------------------------------------------------
// /agriculture/analyze
// ---------------------------------------------------------------------------

export type AnalyzeRequest = {
  point: Coordinate;
  manual_geojson?: Record<string, unknown> | null;
  terrain_id?: string | null;
  yield_objective_q_ha?: number | null;
};

export type AnalyzeResponse = {
  terrain_id: string | null;
  land_profile_id: string | null;
  persisted: boolean;
  parcel: ParcelResolution;
  soil: SoilData;
  weather: WeatherData;
  weather_stats: WeatherStats;
  vegetation: VegetationData;
  dl_observation: DLCropObservation;
  neighbors: NeighborCropContext | null;
  crop_recommendations: CropRecommendationOut[];
  agro_calc_top_crop: AgroCalcEstimate;
  report: AdvisorReport | null;
  warnings: string[];
};

export type ParcelRequest = { point: Coordinate; manual_geojson?: Record<string, unknown> | null };

export class AgricultureApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "AgricultureApiError";
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${AGRICULTURE_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new AgricultureApiError(
      `Impossible de joindre l'agent Agriculture (${AGRICULTURE_API_BASE_URL}). Vérifiez qu'il tourne (uvicorn app.main:app --reload --port 8002).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new AgricultureApiError(
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} de l'agent Agriculture`,
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

/** POST /agriculture/parcel/resolve — aperçu de la parcelle cadastrale/RPG à un point donné, sans persistance. */
export function resolveParcel(request: ParcelRequest): Promise<ParcelResolution> {
  return postJson<ParcelResolution>("/agriculture/parcel/resolve", request);
}

/** POST /agriculture/analyze — pipeline complet (sol/météo/satellite/scoring/rapport), persisté si `terrain_id` est fourni. */
export function analyzeParcel(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/agriculture/analyze", request);
}
