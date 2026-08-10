/**
 * Centralized region configuration with geographic coordinates.
 * This serves as the single source of truth for region data on the frontend.
 * When a new region is added to the system, it should be added here.
 *
 * The backend also maintains its own region list (from detections).
 * This config provides coordinates for map centering and search.
 */

export interface RegionConfig {
  name: string;
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}

export const REGION_COORDS: Record<string, RegionConfig> = {
  "Alsace": { name: "Alsace", latitude: 48.35, longitude: 7.4, latitudeDelta: 1.5, longitudeDelta: 1.5 },
  "Auvergne-Rhone-Alpes": { name: "Auvergne-Rhone-Alpes", latitude: 45.75, longitude: 5.05, latitudeDelta: 3.0, longitudeDelta: 3.0 },
  "Bourgogne-Franche-Comte": { name: "Bourgogne-Franche-Comte", latitude: 47.0, longitude: 4.3, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Bretagne": { name: "Bretagne", latitude: 48.2, longitude: -4.0, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Centre-Val de Loire": { name: "Centre-Val de Loire", latitude: 47.4, longitude: 1.6, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Corse": { name: "Corse", latitude: 42.15, longitude: 9.1, latitudeDelta: 1.5, longitudeDelta: 1.5 },
  "Grand Est": { name: "Grand Est", latitude: 48.6, longitude: 6.2, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Hauts-de-France": { name: "Hauts-de-France", latitude: 49.8, longitude: 2.8, latitudeDelta: 2.0, longitudeDelta: 2.0 },
  "Ile-de-France": { name: "Ile-de-France", latitude: 48.85, longitude: 2.35, latitudeDelta: 1.5, longitudeDelta: 1.5 },
  "Normandie": { name: "Normandie", latitude: 49.1, longitude: -0.4, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Nouvelle-Aquitaine": { name: "Nouvelle-Aquitaine", latitude: 44.8, longitude: -0.5, latitudeDelta: 3.5, longitudeDelta: 3.5 },
  "Occitanie": { name: "Occitanie", latitude: 43.6, longitude: 2.0, latitudeDelta: 3.5, longitudeDelta: 3.5 },
  "Pays de la Loire": { name: "Pays de la Loire", latitude: 47.47, longitude: -0.56, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Provence-Alpes-Cote d'Azur": { name: "Provence-Alpes-Cote d'Azur", latitude: 43.95, longitude: 5.8, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  // Legacy/short names for backward compatibility
  "Auvergne": { name: "Auvergne", latitude: 45.75, longitude: 3.05, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Bourgogne": { name: "Bourgogne", latitude: 47.0, longitude: 4.3, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Centre": { name: "Centre", latitude: 47.4, longitude: 1.6, latitudeDelta: 2.5, longitudeDelta: 2.5 },
  "Champagne": { name: "Champagne", latitude: 49.0, longitude: 3.9, latitudeDelta: 1.8, longitudeDelta: 1.8 },
  "Lorraine": { name: "Lorraine", latitude: 48.9, longitude: 6.2, latitudeDelta: 1.8, longitudeDelta: 1.8 },
  "Nord": { name: "Nord", latitude: 50.4, longitude: 3.0, latitudeDelta: 1.5, longitudeDelta: 1.5 },
  "Picardie": { name: "Picardie", latitude: 49.8, longitude: 2.3, latitudeDelta: 1.8, longitudeDelta: 1.8 },
  "Provence": { name: "Provence", latitude: 43.95, longitude: 5.8, latitudeDelta: 2.5, longitudeDelta: 2.5 },
};

export const FRANCE_COORDS = { latitude: 46.6, longitude: 2.2, latitudeDelta: 8, longitudeDelta: 8 };

/**
 * Get coordinates for a region, with fallback to France center if not found.
 */
export function getRegionCoords(regionName: string): RegionConfig {
  return REGION_COORDS[regionName] || {
    name: regionName,
    latitude: FRANCE_COORDS.latitude,
    longitude: FRANCE_COORDS.longitude,
    latitudeDelta: FRANCE_COORDS.latitudeDelta,
    longitudeDelta: FRANCE_COORDS.longitudeDelta,
  };
}
