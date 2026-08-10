/**
 * Region service - manages fetching and caching of available regions
 * Provides dynamic region data for autocomplete and search
 */

import api from "./api";
import { REGION_COORDS, getRegionCoords } from "../config/regions";

export interface RegionData {
  name: string;
  latitude: number;
  longitude: number;
  detection_count?: number;
}

let cachedRegions: string[] | null = null;
let cachedRegionData: RegionData[] | null = null;

export const regionService = {
  /**
   * Get all available region names.
   * Always includes ALL known French regions from local config,
   * plus any additional regions from the backend that aren't in the config.
   * This ensures the full list is always available even if the backend
   * only has detections for a subset of regions.
   */
  async getAvailableRegions(): Promise<string[]> {
    if (cachedRegions !== null) {
      return cachedRegions;
    }

    // Start with all regions from the local config (always complete)
    const localRegionNames = new Set(Object.keys(REGION_COORDS));

    try {
      // Also fetch from backend to catch any regions not in local config
      const { data } = await api.get<{
        regions: string[];
        total: number;
      }>("/detect/regions/list");

      const backendRegions: string[] = data.regions || [];
      for (const r of backendRegions) {
        localRegionNames.add(r);
      }
    } catch (error) {
      console.warn("Failed to fetch regions from backend:", error);
    }

    cachedRegions = Array.from(localRegionNames).sort((a, b) =>
      a.toLowerCase().localeCompare(b.toLowerCase())
    );
    return cachedRegions;
  },

  /**
   * Get all regions with their coordinates from the backend.
   * Merges database regions with known coordinate data.
   */
  async getRegionCoordinates(): Promise<RegionData[]> {
    if (cachedRegionData !== null) {
      return cachedRegionData;
    }

    try {
      const { data } = await api.get<{
        regions: RegionData[];
        total: number;
      }>("/detect/regions/coordinates");

      cachedRegionData = data.regions || [];
      return cachedRegionData;
    } catch (error) {
      console.error("Failed to fetch region coordinates:", error);
      // Fallback to local config
      cachedRegionData = Object.values(REGION_COORDS).map((r) => ({
        name: r.name,
        latitude: r.latitude,
        longitude: r.longitude,
        detection_count: 0,
      }));
      return cachedRegionData;
    }
  },

  /**
   * Search regions by partial text match (case-insensitive).
   * Useful for autocomplete functionality.
   */
  async searchRegions(query: string): Promise<RegionData[]> {
    const allRegions = await this.getRegionCoordinates();

    if (!query.trim()) {
      return allRegions;
    }

    const lowerQuery = query.toLowerCase().trim();
    return allRegions.filter((region) =>
      region.name.toLowerCase().includes(lowerQuery)
    );
  },

  /**
   * Get coordinates for a specific region.
   * Tries the backend first, falls back to local config.
   */
  async getRegionCoords(regionName: string): Promise<{ latitude: number; longitude: number; latitudeDelta: number; longitudeDelta: number }> {
    const localCoords = getRegionCoords(regionName);
    return {
      latitude: localCoords.latitude,
      longitude: localCoords.longitude,
      latitudeDelta: localCoords.latitudeDelta,
      longitudeDelta: localCoords.longitudeDelta,
    };
  },

  /**
   * Clear the cached regions (useful after data updates).
   */
  clearCache(): void {
    cachedRegions = null;
    cachedRegionData = null;
  },
};
