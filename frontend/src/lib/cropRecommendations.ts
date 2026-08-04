/**
 * `backend/agent_agriculture` expose maintenant `POST /agriculture/analyze`
 * (voir `frontend/src/lib/agricultureApi.ts` et `routes/agriculture.tsx`).
 *
 * `saveRealCropRecommendations` / `loadRealCropRecommendations` mettent en
 * cache (localStorage) la dernière analyse réelle d'une parcelle, pour que
 * `business.tsx` puisse la réutiliser directement plutôt que d'envoyer les
 * données factices ci-dessous à l'agent Business — même principe que
 * `lib/terrain.ts`. Tant qu'aucune analyse réelle n'a été faite (ou que le
 * cache a expiré), `business.tsx` retombe sur `MOCK_CROP_RECOMMENDATIONS`
 * pour rester utilisable de façon indépendante (cf. README agent_business
 * §"Prochaines étapes").
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

export const MOCK_TERRAIN_ID = "11111111-1111-1111-1111-111111111111";

export const MOCK_CROP_RECOMMENDATIONS: CropRecommendation[] = [
  {
    rang: 1,
    culture: "tomate",
    score_compatibilite: 92,
    cycle_jours: 90,
    besoins_irrigation: { niveau: "eleve", mm_par_semaine: 35 },
    besoins_engrais: { azote_kg_ha: 120, phosphore_kg_ha: 60, potassium_kg_ha: 150 },
    besoins_pesticides: { traitements_par_saison: 4, type: "fongicide + insecticide" },
    feature_importance: { sol_ph: 0.32, ensoleillement: 0.28, temperature_moyenne: 0.24, historique_rpg: 0.16 },
  },
  {
    rang: 2,
    culture: "pomme_de_terre",
    score_compatibilite: 87,
    cycle_jours: 110,
    besoins_irrigation: { niveau: "modere", mm_par_semaine: 25 },
    besoins_engrais: { azote_kg_ha: 150, phosphore_kg_ha: 80, potassium_kg_ha: 200 },
    besoins_pesticides: { traitements_par_saison: 3, type: "fongicide (mildiou)" },
    feature_importance: { sol_texture: 0.35, drainage: 0.30, temperature_moyenne: 0.20, historique_rpg: 0.15 },
  },
  {
    rang: 3,
    culture: "ble",
    score_compatibilite: 81,
    cycle_jours: 240,
    besoins_irrigation: { niveau: "faible", mm_par_semaine: 10 },
    besoins_engrais: { azote_kg_ha: 180, phosphore_kg_ha: 50, potassium_kg_ha: 60 },
    besoins_pesticides: { traitements_par_saison: 2, type: "fongicide leger" },
    feature_importance: { sol_ph: 0.30, historique_rpg: 0.30, ensoleillement: 0.22, temperature_moyenne: 0.18 },
  },
  {
    rang: 4,
    culture: "mais",
    score_compatibilite: 76,
    cycle_jours: 150,
    besoins_irrigation: { niveau: "eleve", mm_par_semaine: 30 },
    besoins_engrais: { azote_kg_ha: 200, phosphore_kg_ha: 70, potassium_kg_ha: 100 },
    besoins_pesticides: { traitements_par_saison: 2, type: "herbicide + insecticide" },
    feature_importance: { temperature_moyenne: 0.34, sol_texture: 0.28, ensoleillement: 0.20, historique_rpg: 0.18 },
  },
  {
    rang: 5,
    culture: "tournesol",
    score_compatibilite: 70,
    cycle_jours: 130,
    besoins_irrigation: { niveau: "faible", mm_par_semaine: 8 },
    besoins_engrais: { azote_kg_ha: 60, phosphore_kg_ha: 40, potassium_kg_ha: 50 },
    besoins_pesticides: { traitements_par_saison: 1, type: "surveillance oiseaux" },
    feature_importance: { ensoleillement: 0.40, sol_ph: 0.25, temperature_moyenne: 0.20, historique_rpg: 0.15 },
  },
];

const CULTURE_LABELS: Record<string, string> = {
  tomate: "Tomate",
  pomme_de_terre: "Pomme de terre",
  ble: "Blé",
  // Les 9 cultures notées par `backend/agent_agriculture/app/services/ml_service.py`
  // (voir `_CROP_PROFILES`) — clés distinctes des données factices ci-dessus.
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
