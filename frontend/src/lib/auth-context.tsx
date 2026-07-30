import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  signIn as apiSignIn,
  signUp as apiSignUp,
  fetchMe,
  type AuthResponse,
  type Role,
  type SignInRequest,
  type SignUpRequest,
  type UserOut,
} from "@/lib/authApi";

const SESSION_KEY = "agriguide.session";

// --- DEV ONLY : contournement temporaire du service Auth réel (backend/auth + Postgres). ---
// Permet de se connecter et de naviguer dans le site sans base de données ni service Auth
// démarré. À retirer une fois le service Auth (Postgres) disponible en local :
// il suffit de supprimer ce bloc et le `if` correspondant dans `signIn` ci-dessous.
const DEV_MOCK_CREDENTIALS: SignInRequest = { email: "demo@agriguide.fr", password: "demo1234" };
const DEV_MOCK_USER: UserOut = {
  id: "dev-mock-user-id",
  email: DEV_MOCK_CREDENTIALS.email,
  nom: "Jean Demo",
  telephone: null,
  role: "farmer",
  equipements: [],
  terrains: [],
};
const DEV_MOCK_AUTH_RESPONSE: AuthResponse = {
  access_token: "dev-mock-token",
  token_type: "bearer",
  user: DEV_MOCK_USER,
};
// --- FIN DEV ONLY ---

type StoredSession = { token: string; user: UserOut };

function loadStoredSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.token === "string" && parsed.user) return parsed as StoredSession;
    return null;
  } catch {
    return null;
  }
}

function saveStoredSession(session: StoredSession | null) {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    // ignore (mode privé, quota...)
  }
}

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: UserOut | null;
  token: string | null;
  signIn: (payload: SignInRequest) => Promise<UserOut>;
  signUp: (payload: SignUpRequest) => Promise<UserOut>;
  signOut: () => void;
  setUser: (user: UserOut) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<StoredSession | null>(null);

  // Le localStorage n'existe pas côté serveur (SSR) — on charge la session
  // uniquement après le montage côté client, comme lib/terrain.ts.
  useEffect(() => {
    const stored = loadStoredSession();
    if (!stored) {
      setStatus("anonymous");
      return;
    }
    setSession(stored);
    setStatus("authenticated");

    // Revalidation en tâche de fond : si le token est encore valide, on
    // rafraîchit le profil (utile après une modif faite ailleurs) ; si le
    // service Auth est injoignable ou le token expiré, on garde la session
    // en cache plutôt que de déconnecter brutalement l'utilisateur.
    fetchMe(stored.token)
      .then((user) => {
        const refreshed = { token: stored.token, user };
        setSession(refreshed);
        saveStoredSession(refreshed);
      })
      .catch(() => {
        /* silencieux : on garde la session en cache */
      });
  }, []);

  const applyAuthResponse = useCallback((response: AuthResponse): UserOut => {
    const next = { token: response.access_token, user: response.user };
    setSession(next);
    saveStoredSession(next);
    setStatus("authenticated");
    return response.user;
  }, []);

  const signIn = useCallback(
    async (payload: SignInRequest) => {
      // DEV ONLY : voir DEV_MOCK_CREDENTIALS plus haut.
      if (
        payload.email === DEV_MOCK_CREDENTIALS.email &&
        payload.password === DEV_MOCK_CREDENTIALS.password
      ) {
        return applyAuthResponse(DEV_MOCK_AUTH_RESPONSE);
      }
      return applyAuthResponse(await apiSignIn(payload));
    },
    [applyAuthResponse],
  );

  const signUp = useCallback(
    async (payload: SignUpRequest) => applyAuthResponse(await apiSignUp(payload)),
    [applyAuthResponse],
  );

  const signOut = useCallback(() => {
    setSession(null);
    saveStoredSession(null);
    setStatus("anonymous");
  }, []);

  const setUser = useCallback((user: UserOut) => {
    setSession((prev) => {
      if (!prev) return prev;
      const next = { token: prev.token, user };
      saveStoredSession(next);
      return next;
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: session?.user ?? null,
      token: session?.token ?? null,
      signIn,
      signUp,
      signOut,
      setUser,
    }),
    [status, session, signIn, signUp, signOut, setUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé à l'intérieur de <AuthProvider>");
  return ctx;
}

export function roleLabel(role: Role): string {
  return role === "farmer" ? "Agriculteur" : "Acheteur";
}
