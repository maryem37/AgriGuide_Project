import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_BASE_URL } from "../utils/config";
import { farmerManager } from "../utils/farmerManager";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Registered by AuthProvider so a failed session actually logs the user out
// instead of leaving the app stuck in a "logged in" state with no token.
let onAuthFailure: (() => void) | null = null;

export function setAuthFailureHandler(handler: (() => void) | null) {
  onAuthFailure = handler;
}

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const farmerId = await farmerManager.getFarmerId();
  if (farmerId) {
    config.headers["X-Farmer-ID"] = farmerId;
    config.headers["farmer_id"] = farmerId;
  }

  console.log(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url} (farmer_id: ${farmerId})`);
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} -> ${response.status}`);
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "unknown";
    const method = error.config?.method?.toUpperCase() || "UNKNOWN";

    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      console.error(`[API] ${method} ${url} TIMEOUT after ${error.config?.timeout}ms`);
    } else if (error.message === "Network request failed" || !error.response) {
      console.error(`[API] ${method} ${url} NETWORK ERROR: ${error.message}. Is the backend running?`);
    } else {
      console.error(`[API] ${method} ${url} -> ${status}: ${JSON.stringify(error.response?.data)}`);
    }

    // 401 = invalid/expired token. 403 "Not authenticated" = no token was sent
    // at all (which happens once the 401 above cleared it from storage).
    const isAuthFailure =
      status === 401 ||
      (status === 403 && error.response?.data?.detail === "Not authenticated");

    if (isAuthFailure) {
      await AsyncStorage.removeItem("auth_token");
      await AsyncStorage.removeItem("user_data");
      onAuthFailure?.();
    }
    return Promise.reject(error);
  }
);

export default api;
