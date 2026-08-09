/**
 * `backend/agent_agriculture` expose maintenant `POST /agriculture/analyze`
 * (voir `frontend/src/lib/agricultureApi.ts` et `routes/agriculture.tsx`).
 *
 * `saveRealCropRecommendations` / `loadRealCropRecommendations` mettent en
 * cache (localStorage) la dernière analyse réelle d'une parcelle, pour que
 * `business.tsx` puisse la réutiliser directement. Sans analyse réelle,
 * l'interface demande au farmer de passer d'abord par le Conseiller
 * Agriculture; aucun scénario financier n'est fabriqué.
 */

import type { CropRecommendation } from "@/lib/businessApi";

const REAL_RECOMMENDATIONS_KEY = "agriguide.agriculture.crop_recommendations";

type StoredRealRecommendations = {
  terrainId: string;
  recommendations: CropRecommendation[];
  savedAt: string;
};

export function saveRealCropRecommendations(terrainId: string, recommendations: CropRecommendation[]) {
  try {
    const payload: StoredRealRecommendations = { terrainId, recommendations, savedAt: new Date().toISOString() };
    localStorage.setItem(REAL_RECOMMENDATIONS_KEY, JSON.stringify(payload));
  } catch {
    // ignore (mode privé, quota...)
  }
}

/** Renvoie l'analyse réelle la plus récente pour ce terrain, ou `null` si aucune n'existe encore. */
export function loadRealCropRecommendations(terrainId: string): CropRecommendation[] | null {
  try {
    const raw = localStorage.getItem(REAL_RECOMMENDATIONS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredRealRecommendations;
    if (parsed.terrainId !== terrainId || !Array.isArray(parsed.recommendations)) return null;
    return parsed.recommendations;
  } catch {
    return null;
  }
}

/** Terrain analysé en dernier par le Conseiller Agriculture, ou `null`. */
export function getLatestAnalyzedTerrainId(): string | null {
  try {
    const raw = localStorage.getItem(REAL_RECOMMENDATIONS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredRealRecommendations;
    return parsed.terrainId || null;
  } catch {
    return null;
  }
}

const CULTURE_LABELS: Record<string, string> = {
  tomate: "Tomate",
  pomme_de_terre: "Pomme de terre",
  ble: "Blé",
  // Les 9 cultures notées par `backend/agent_agriculture/app/services/ml_service.py`
  // (voir `_CROP_PROFILES`).
  ble_tendre: "Blé tendre",
  colza: "Colza",
  orge: "Orge",
  mais: "Maïs",
  tournesol: "Tournesol",
  betterave_sucriere: "Betterave sucrière",
  soja: "Soja",
  pois_proteagineux: "Pois protéagineux",
};

export function cultureLabel(culture: string): string {
  return CULTURE_LABELS[culture] ?? culture;
}
