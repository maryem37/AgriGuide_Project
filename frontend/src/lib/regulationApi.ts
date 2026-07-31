/**
 * Client API pour l'agent Régulation (backend/agent_regulation).
 *
 * Les types ci-dessous reflètent volontairement, champ à champ,
 * `backend/agent_regulation/app/schemas/chat.py` pour éviter tout mapping
 * caché entre les deux couches.
 *
 * URL du service : `VITE_AGENT_REGULATION_URL` (défaut : http://localhost:8001,
 * cf. `backend/agent_regulation/README.md` — `uvicorn app.main:app --reload --port 8001`).
 * Port distinct de l'agent Business (8000) pour pouvoir lancer les deux en local.
 */

const REGULATION_API_BASE_URL: string =
  (import.meta.env.VITE_AGENT_REGULATION_URL as string | undefined) ?? "http://localhost:8001";

// ---------------------------------------------------------------------------
// Entrée/sortie — reflète ChatRequest / ChatResponse
// ---------------------------------------------------------------------------

export type ChatRequest = {
  question: string;
};

export type ChatResponse = {
  answer: string;
};

export class RegulationApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "RegulationApiError";
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${REGULATION_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new RegulationApiError(
      `Impossible de joindre l'agent Régulation (${REGULATION_API_BASE_URL}). Vérifiez qu'il tourne (uvicorn app.main:app --reload --port 8001).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new RegulationApiError(
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} de l'agent Régulation`),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

/** POST /chat — pose une question de réglementation agricole à l'agent. */
export function askRegulationAgent(request: ChatRequest): Promise<ChatResponse> {
  return postJson<ChatResponse>("/chat", request);
}
