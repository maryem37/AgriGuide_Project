/**
 * Client API pour l'agent Monitoring (backend/agent_monitoring).
 *
 * Types alignés sur `backend/agent_monitoring/app/models/schemas.py`.
 *
 * URL : `VITE_AGENT_MONITORING_URL` (défaut http://localhost:8003).
 */

const MONITORING_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_MONITORING_URL as string | undefined) ??
  "http://localhost:8003";

export type LocationInput = {
  latitude: number;
  longitude: number;
  label?: string | null;
};

export type CropContext = {
  crop_name: string;
  hectares: number;
  growth_stage?: string | null;
  soil_type?: string | null;
  water_sensitivity?: string | null;
};

export type AnalyzeRequest = {
  farmer_name: string;
  location: LocationInput;
  crops: CropContext[];
  hardware_inventory?: string[];
  terrain_id?: string | null;
};

export type WeatherSummary = {
  location_label?: string | null;
  today_max_temp_c?: number | null;
  today_min_temp_c?: number | null;
  precipitation_sum_mm?: number | null;
  precipitation_probability_pct?: number | null;
  max_wind_speed_kmh?: number | null;
  conditions_label?: string | null;
  note?: string | null;
};

export type CropAlert = {
  crop: string;
  risk: "low" | "medium" | "high" | string;
  message: string;
  action: string;
};

export type AnalysisResult = {
  has_alert: boolean;
  alert_message?: string | null;
  daily_advice: string;
  water_saving_technique: string;
  tasks: string[];
  crop_alerts: CropAlert[];
};

export type AnalyzeResponse = {
  farmer_name: string;
  location?: string | null;
  terrain_id?: string | null;
  crops: CropContext[];
  weather_summary: WeatherSummary;
  analysis: AnalysisResult;
};

export class MonitoringApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "MonitoringApiError";
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${MONITORING_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new MonitoringApiError(
      `Impossible de joindre l'agent Monitoring (${MONITORING_API_BASE_URL}). Vérifiez qu'il tourne (uvicorn app.main:app --reload --port 8003).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new MonitoringApiError(
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} de l'agent Monitoring`,
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

/** POST /monitoring/analyze — briefing quotidien météo + conseils. */
export function analyzeMonitoringDay(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/monitoring/analyze", request);
}
