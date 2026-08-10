import Constants from "expo-constants";
import { Platform } from "react-native";

const API_PORT = 8080;

/** Private LAN IPs only — ignore tunnel/ngrok hosts for API routing. */
function isPrivateLanHost(host: string): boolean {
  return /^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)/.test(host);
}

function getApiHost(): string {
  const debuggerHost =
    Constants.expoGoConfig?.debuggerHost ?? Constants.expoConfig?.hostUri;

  if (debuggerHost) {
    const host = debuggerHost.split(":")[0];
    if (host && isPrivateLanHost(host)) {
      console.log(`[Config] Using LAN IP from Expo debuggerHost: ${host}:${API_PORT}`);
      return `${host}:${API_PORT}`;
    }
  }

  const envHost =
    (Constants.expoConfig?.extra?.apiHost as string | undefined) ||
    (process.env.EXPO_PUBLIC_API_HOST as string | undefined);

  if (envHost) {
    console.log(`[Config] Using env/app.json API host: ${envHost}`);
    return envHost;
  }

  if (Platform.OS === "android") {
    console.log(`[Config] Using Android emulator fallback: 10.0.2.2:${API_PORT}`);
    return `10.0.2.2:${API_PORT}`;
  }
  console.log(`[Config] Using localhost fallback: localhost:${API_PORT}`);
  return `localhost:${API_PORT}`;
}

const apiHost = getApiHost();

export const API_BASE_URL = `http://${apiHost}/api`;
export const API_IMAGE_URL = `http://${apiHost}`;

// NOTE: Risk colors are centralized in utils/theme.ts (RISK_CONFIGS).
// Do NOT define duplicate color mappings here. Import from theme.ts instead.
