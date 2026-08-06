/**
 * Client HTTP pour l'agent Déchets / Valorisation
 * (`backend/waste_agents` — uvicorn api.main:app --port 8004).
 *
 * Lecture seule de canonical_knowledge.json : pas de clé LLM requise.
 */

const WASTE_API_BASE_URL =
  (import.meta.env.VITE_AGENT_WASTE_URL as string | undefined) ?? "http://localhost:8004";

export class WasteApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "WasteApiError";
    this.status = status;
  }
}

export type TransformationOut = {
  process: string;
  process_label: string;
  output_product: string;
  output_label: string;
  description: string;
};

export type ApplicationOut = {
  name: string;
  name_label: string;
  category: string;
  description: string;
  environmental_benefit?: string | null;
};

export type WasteOut = {
  id: string;
  name: string;
  name_label: string;
  category: string;
  plant_part: string;
  description: string;
  composition_summary: string[];
  transformations: TransformationOut[];
  final_products: string[];
  final_products_labels: string[];
  applications: ApplicationOut[];
  advantages: string[];
  confidence: number;
  marketplace_title: string;
  marketplace_utility: string;
  marketplace_description: string;
};

export type CropWasteProfile = {
  culture: string;
  kb_crop_name: string | null;
  crop_label_fr: string;
  found: boolean;
  scientific_name: string;
  wastes: WasteOut[];
  message: string;
};

export type ForCropsResponse = {
  profiles: CropWasteProfile[];
};

export type MarketplaceSuggestionsResponse = {
  culture: string;
  crop_label_fr: string;
  found: boolean;
  harvest_hint: string;
  suggestions: WasteOut[];
  message: string;
};

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    return JSON.stringify(body?.detail ?? body);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

export async function fetchWasteProfilesForCrops(cultures: string[]): Promise<ForCropsResponse> {
  let res: Response;
  try {
    res = await fetch(`${WASTE_API_BASE_URL}/waste/for-crops`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cultures }),
    });
  } catch {
    throw new WasteApiError(
      `Impossible de joindre l'agent Déchets (${WASTE_API_BASE_URL}). Lancez : uvicorn api.main:app --reload --port 8004`,
    );
  }
  if (!res.ok) throw new WasteApiError(await parseError(res), res.status);
  return res.json() as Promise<ForCropsResponse>;
}

export async function fetchMarketplaceWasteSuggestions(
  culture: string,
  limit = 4,
): Promise<MarketplaceSuggestionsResponse> {
  const qs = new URLSearchParams({ culture, limit: String(limit) });
  let res: Response;
  try {
    res = await fetch(`${WASTE_API_BASE_URL}/waste/marketplace-suggestions?${qs}`);
  } catch {
    throw new WasteApiError(
      `Impossible de joindre l'agent Déchets (${WASTE_API_BASE_URL}). Lancez : uvicorn api.main:app --reload --port 8004`,
    );
  }
  if (!res.ok) throw new WasteApiError(await parseError(res), res.status);
  return res.json() as Promise<MarketplaceSuggestionsResponse>;
}
