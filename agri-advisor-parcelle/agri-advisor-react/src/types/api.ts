/**
 * Mirrors schemas.py exactly. If the backend schema changes, update here too —
 * this file is the single source of truth for API shapes on the frontend.
 */

export interface Coordinate {
  lat: number;
  lon: number;
}

export interface ParcelRequest {
  point: Coordinate;
  manual_geojson?: GeoJsonGeometry | null;
}

export type GeoJsonGeometry = {
  type: string;
  coordinates: unknown;
};

export type ParcelSource = "cadastre" | "rpg" | "manual" | "unresolved";

export interface ParcelResolution {
  resolved: boolean;
  source: ParcelSource;
  geometry?: GeoJsonGeometry | null;
  centroid?: Coordinate | null;
  parcel_id?: string | null;
  rpg_id_parcel?: string | null;
  area_ha?: number | null;
  area_m2?: number | null;
  crop_declared?: string | null;
  is_agricultural?: boolean | null;
  agricultural_note?: string | null;
  warning?: string | null;
}

export interface NeighborParcel {
  geometry: GeoJsonGeometry;
  crop_code?: string | null;
}

export interface NeighborCropContext {
  neighbor_count: number;
  crop_distribution_pct: Record<string, number>;
  neighbors: NeighborParcel[];
  note: string;
}

export interface AdvisorReport {
  parcel_id?: string | null;
  report_markdown: string;
  warnings: string[];
  unverified_figures: string[];
}

export interface NdviHeatmapBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface NdviHeatmapResponse {
  image_base64: string;
  bounds: NdviHeatmapBounds;
}
