/**
 * Espace réservé pour la sortie de l'agent Agriculture (`crop_recommendations`).
 *
 * `backend/agent_agriculture` n'expose pas encore d'endpoint HTTP (voir son
 * README), donc en attendant on envoie à l'agent Business les mêmes données
 * factices que celui-ci utilise déjà en interne
 * (`backend/agent_business/app/data/mock_crop_recommendations.py`), pour que
 * les scénarios affichés soient cohérents avec sa propre démo.
 *
 * À remplacer par un vrai appel à `POST /agriculture/analyze` une fois cet
 * agent branché — le reste du flux (business.tsx, businessApi.ts) n'aura pas
 * à changer, seul l'appelant de `crop_recommendations` change.
 */

import type { CropRecommendation } from "@/lib/businessApi";

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
  mais: "Maïs",
  tournesol: "Tournesol",
};

export function cultureLabel(culture: string): string {
  return CULTURE_LABELS[culture] ?? culture;
}
