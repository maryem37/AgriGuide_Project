import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "../utils/config";

interface ConnectivityState {
  isChecking: boolean;
  isConnected: boolean;
  serverUrl: string;
  error: string | null;
}

export function useConnectivity(): ConnectivityState & { retry: () => void } {
  const [state, setState] = useState<ConnectivityState>({
    isChecking: true,
    isConnected: false,
    serverUrl: API_BASE_URL,
    error: null,
  });

  const check = useCallback(async () => {
    setState((prev) => ({ ...prev, isChecking: true, error: null }));

    try {
      const healthUrl = `${API_BASE_URL.replace(/\/api\/?$/, "")}/health`;
      console.log(`[Connectivity] Checking ${healthUrl}`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const response = await fetch(healthUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        console.log("[Connectivity] Server reachable:", data);
        setState((prev) => ({
          ...prev,
          isChecking: false,
          isConnected: true,
          error: null,
        }));
      } else {
        console.warn("[Connectivity] Server returned status:", response.status);
        setState((prev) => ({
          ...prev,
          isChecking: false,
          isConnected: false,
          error: `Server returned status ${response.status}`,
        }));
      }
    } catch (err: any) {
      console.warn("[Connectivity] Connection failed:", err.name, err.message);
      const message =
        err.name === "AbortError"
          ? "Connection timed out. Is the backend running?"
          : err.message === "Network request failed"
            ? "Cannot reach server. Make sure you are on the same WiFi network as the PC running the backend."
            : err.message || "Connection failed";
      setState((prev) => ({
        ...prev,
        isChecking: false,
        isConnected: false,
        error: message,
      }));
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return { ...state, retry: check };
}
