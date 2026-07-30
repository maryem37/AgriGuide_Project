import type {
  AdvisorReport,
  Coordinate,
  NdviHeatmapResponse,
  NeighborCropContext,
  ParcelResolution,
} from "../types/api";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || "http://127.0.0.1:8000";

/**
 * Thrown for any non-2xx response. Carries the backend's `detail` field
 * (FastAPI's HTTPException shape) when present, so callers can show the
 * real reason instead of a generic "something went wrong".
 */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      `Impossible de contacter le serveur (${API_BASE}). Le backend est-il démarré ` +
        `(uvicorn main:app --reload) et le CORS est-il autorisé pour cette origine ?`,
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText || `Erreur ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* body wasn't JSON — keep statusText */
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as T;
}

export function resolveParcel(point: Coordinate): Promise<ParcelResolution> {
  return postJSON<ParcelResolution>("/parcel/resolve", { point, manual_geojson: null });
}

export function getNeighbors(point: Coordinate, radiusM = 800): Promise<NeighborCropContext> {
  return postJSON<NeighborCropContext>(`/parcel/neighbors?radius_m=${radiusM}`, {
    point,
    manual_geojson: null,
  });
}

export function advise(point: Coordinate): Promise<AdvisorReport> {
  return postJSON<AdvisorReport>("/advise", { point, manual_geojson: null });
}

export function getNdviHeatmap(point: Coordinate): Promise<NdviHeatmapResponse> {
  return postJSON<NdviHeatmapResponse>("/parcel/ndvi_heatmap", { point, manual_geojson: null });
}
