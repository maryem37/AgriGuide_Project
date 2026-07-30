/**
 * Client API pour le service Auth (backend/auth).
 *
 * Types alignés champ à champ sur `backend/auth/app/models/schemas.py`.
 *
 * URL du service : `VITE_AUTH_API_URL` (défaut : http://localhost:8001,
 * cf. `backend/auth/README.md` — `uvicorn app.main:app --reload --port 8001`).
 */

const AUTH_API_BASE_URL: string =
  (import.meta.env.VITE_AUTH_API_URL as string | undefined) ?? "http://localhost:8001";

export type Role = "farmer" | "acheteur";

export type EquipementType =
  | "tracteur"
  | "cultivateur"
  | "fraise_rotative"
  | "planteuse"
  | "moissonneuse_batteuse"
  | "remorque_agricole"
  | "pulverisateur"
  | "tunnel_plastique";

export type LatLng = [number, number];

export type TerrainInput = {
  nom: string;
  points: LatLng[];
  superficie_ha?: number;
  region?: string | null;
};

export type TerrainUpdateInput = Partial<TerrainInput>;

export type TerrainOut = {
  id: string;
  nom: string | null;
  superficie_ha: number;
  region: string | null;
  points: LatLng[];
};

export type UserOut = {
  id: string;
  email: string;
  nom: string;
  telephone: string | null;
  role: Role;
  equipements: EquipementType[];
  terrains: TerrainOut[];
};

export type SignUpRequest = {
  email: string;
  password: string;
  nom: string;
  telephone?: string;
  role: Role;
  equipements?: EquipementType[];
  terrains?: TerrainInput[];
};

export type SignInRequest = {
  email: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: UserOut;
};

export class AuthApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

async function request<TResponse>(
  path: string,
  options: { method: string; body?: unknown; token?: string },
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${AUTH_API_BASE_URL}${path}`, {
      method: options.method,
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new AuthApiError(
      `Impossible de joindre le service Auth (${AUTH_API_BASE_URL}). Vérifiez qu'il tourne (uvicorn app.main:app --reload --port 8001).`,
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new AuthApiError(
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Erreur ${response.status} du service Auth`,
      response.status,
    );
  }

  if (response.status === 204) return undefined as TResponse;
  return response.json() as Promise<TResponse>;
}

export function signUp(payload: SignUpRequest): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/signup", { method: "POST", body: payload });
}

export function signIn(payload: SignInRequest): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/signin", { method: "POST", body: payload });
}

export function fetchMe(token: string): Promise<UserOut> {
  return request<UserOut>("/auth/me", { method: "GET", token });
}

export function updateEquipements(token: string, equipements: EquipementType[]): Promise<UserOut> {
  return request<UserOut>("/auth/me/equipements", {
    method: "PUT",
    body: { equipements },
    token,
  });
}

export function addTerrain(token: string, terrain: TerrainInput): Promise<TerrainOut> {
  return request<TerrainOut>("/auth/me/terrains", { method: "POST", body: terrain, token });
}

export function updateTerrain(
  token: string,
  terrainId: string,
  patch: TerrainUpdateInput,
): Promise<TerrainOut> {
  return request<TerrainOut>(`/auth/me/terrains/${terrainId}`, {
    method: "PUT",
    body: patch,
    token,
  });
}

export function deleteTerrain(token: string, terrainId: string): Promise<void> {
  return request<void>(`/auth/me/terrains/${terrainId}`, { method: "DELETE", token });
}
