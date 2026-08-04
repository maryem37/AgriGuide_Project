/**
 * Cache local de la dernière décision business confirmée, pour que
 * `/aujourd-hui` puisse brancher l'agent Monitoring sans attendre la
 * persistance PostgreSQL de `farmer_decisions` (encore TODO côté Business).
 */

import type { FarmerDecisionResponse } from "@/lib/businessApi";

const DECISION_KEY = "agriguide.business.farmer_decision";

type StoredDecision = {
  decision: FarmerDecisionResponse;
  savedAt: string;
};

export function saveFarmerDecision(decision: FarmerDecisionResponse) {
  try {
    const payload: StoredDecision = { decision, savedAt: new Date().toISOString() };
    localStorage.setItem(DECISION_KEY, JSON.stringify(payload));
  } catch {
    // ignore (mode privé, quota...)
  }
}

/** Dernière décision pour ce terrain, ou `null`. */
export function loadFarmerDecision(terrainId: string): FarmerDecisionResponse | null {
  try {
    const raw = localStorage.getItem(DECISION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredDecision;
    if (!parsed?.decision || parsed.decision.terrain_id !== terrainId) return null;
    return parsed.decision;
  } catch {
    return null;
  }
}

export function clearFarmerDecision() {
  try {
    localStorage.removeItem(DECISION_KEY);
  } catch {
    // ignore
  }
}
