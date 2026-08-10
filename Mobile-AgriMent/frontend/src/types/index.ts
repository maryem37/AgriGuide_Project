export type Region = string;

// Fallback region list used only when backend is unreachable.
// Regions are normally fetched dynamically from the backend via regionService.
export const REGIONS_FALLBACK: Region[] = [
  "Alsace",
  "Auvergne-Rhone-Alpes",
  "Bourgogne-Franche-Comte",
  "Bretagne",
  "Centre-Val de Loire",
  "Corse",
  "Grand Est",
  "Hauts-de-France",
  "Ile-de-France",
  "Normandie",
  "Nouvelle-Aquitaine",
  "Occitanie",
  "Pays de la Loire",
  "Provence-Alpes-Cote d'Azur",
];

export interface User {
  id: string;
  name: string;
  email: string;
  region: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Detection {
  id: string;
  species: string;
  scientific_name: string;
  confidence: number;
  risk: "low" | "medium" | "high" | "critical";
  description: string;
  recommendation: string;
  image_url: string;
  region: Region;
  latitude?: number | null;
  longitude?: number | null;
  created_at: string;
  notified_count: number;
}

export interface DetectionHistoryResponse {
  detections: Detection[];
  total: number;
}

export interface Notification {
  id: string;
  detection_id?: string;
  title: string;
  message: string;
  species: string;
  region: Region;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
  total: number;
}

// Route params for the root stack navigator. Used to type the shared
// navigationRef in src/utils/notifications.ts so notification taps can
// navigate to the correct screen.
export type RootStackParamList = {
  Login: undefined;
  HomeTab: undefined;
  Detect: undefined;
  Result: { detection: Detection };
  Notifications: undefined;
  NotificationDetail: { notification: Notification };
  Map: { refreshKey?: number; highlightedDetectionId?: string; highlightedRegion?: string } | undefined;
  History: undefined;
  Profile: undefined;
};
