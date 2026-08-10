import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
  Platform,
  TextInput,
  Keyboard,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { Header } from "../components";
import { MapContentView } from "../components/MapView";
import { useAuth } from "../context/AuthContext";
import { detectionService } from "../services/detection";
import { regionService } from "../services/region";
import { Detection } from "../types";
import { RISK_FILTERS, getRiskConfig } from "../utils/theme";
import { FRANCE_COORDS, getRegionCoords } from "../config/regions";

const { width } = Dimensions.get("window");

// Polling interval for fetching new detections (ms)
const POLL_INTERVAL = 30000;

export default function MapScreen({ navigation, route }: any) {
  const { user } = useAuth();
  const initialRegion = route?.params?.highlightedRegion || user?.region || "";
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(initialRegion);
  const [activeRegion, setActiveRegion] = useState(route?.params?.highlightedRegion || "All");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [riskFilter, setRiskFilter] = useState("all");
  const [mapRegion, setMapRegion] = useState(
    route?.params?.highlightedRegion
      ? (() => {
          const rc = getRegionCoords(route.params.highlightedRegion);
          return { latitude: rc.latitude, longitude: rc.longitude, latitudeDelta: rc.latitudeDelta, longitudeDelta: rc.longitudeDelta };
        })()
      : FRANCE_COORDS
  );
  const [mapReady, setMapReady] = useState(false);
  const [availableRegions, setAvailableRegions] = useState<string[]>([]);
  const [geoSuggestions, setGeoSuggestions] = useState<{ name: string; latitude: number; longitude: number }[]>([]);
  const [geoLoading, setGeoLoading] = useState(false);
  const mapRef = useRef<any>(null);
  const hasFitRef = useRef(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Ref to always hold the latest activeRegion without recreating loadDetections
  const activeRegionRef = useRef(activeRegion);

  // Keep ref in sync with state
  useEffect(() => {
    activeRegionRef.current = activeRegion;
  }, [activeRegion]);

  // Fetch dynamic regions on mount
  useEffect(() => {
    (async () => {
      try {
        const regions = await regionService.getAvailableRegions();
        if (regions && regions.length > 0) {
          setAvailableRegions(regions);
        }
      } catch (error) {
        console.warn("Failed to fetch regions:", error);
      }
    })();
  }, []);

  // Filter regions by search query for autocomplete
  const filteredRegions = availableRegions.filter((r) =>
    r.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Debounced geocode: when query looks like a place name (not matching a region),
  // fetch real geocoded suggestions via Nominatim (OpenStreetMap) — works on all platforms.
  useEffect(() => {
    const query = searchQuery.trim();
    if (query.length < 2 || filteredRegions.some(r => r.toLowerCase() === query.toLowerCase())) {
      setGeoSuggestions([]);
      return;
    }
    setGeoLoading(true);
    const timer = setTimeout(async () => {
      try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query + ", France")}&format=json&limit=5&accept-language=fr`;
        const res = await fetch(url, {
          headers: { "User-Agent": "AgriMent/1.0" },
        });
        const data = await res.json();
        setGeoSuggestions(
          data.map((item: any) => ({
            name: item.display_name.split(",")[0],
            latitude: parseFloat(item.lat),
            longitude: parseFloat(item.lon),
          }))
        );
      } catch {
        setGeoSuggestions([]);
      } finally {
        setGeoLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // FIX: Use a ref for activeRegion so this function is stable and never stale.
  // This prevents stale closures in polling intervals and focus effects.
  const loadDetections = useCallback(async () => {
    try {
      const region = activeRegionRef.current;
      let data;
      if (region === "All") {
        data = await detectionService.getAllDetections();
      } else {
        data = await detectionService.getRegionDetections(region);
      }
      setDetections(data.detections);
      hasFitRef.current = false;
    } catch (error) {
      console.warn("Failed to load detections:", error);
    } finally {
      setLoading(false);
    }
  }, []); // No dependencies — always reads from ref

  // FIX: Use useFocusEffect for screen focus (sets up polling).
  // Also add a separate useEffect for refreshKey to handle navigation.replace
  // which may not trigger useFocusEffect reliably in all cases.
  useFocusEffect(
    useCallback(() => {
      loadDetections();

      pollRef.current = setInterval(() => {
        loadDetections();
      }, POLL_INTERVAL);

      return () => {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };
    }, [loadDetections])
  );

  // FIX: When navigated to with refreshKey (e.g. after sending an alert),
  // force a refetch with multiple retries to handle race conditions.
  // The detection is committed to DB before the response is sent, but
  // SQLite WAL/async session pooling can cause a brief read-after-write
  // visibility gap. We refetch immediately, then again at 500ms and 1500ms.
  useEffect(() => {
    if (route?.params?.refreshKey) {
      loadDetections();
      const t1 = setTimeout(() => loadDetections(), 500);
      const t2 = setTimeout(() => loadDetections(), 1500);
      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
      };
    }
  }, [route?.params?.refreshKey, loadDetections]);

  const selectRegion = (region: string) => {
    setActiveRegion(region);
    setSearchQuery(region === "All" ? "" : region);
    setShowSuggestions(false);
    Keyboard.dismiss();
    const coords = region === "All"
      ? FRANCE_COORDS
      : (() => {
          const rc = getRegionCoords(region);
          return { latitude: rc.latitude, longitude: rc.longitude, latitudeDelta: rc.latitudeDelta, longitudeDelta: rc.longitudeDelta };
        })();
    setMapRegion(coords);
    if (mapRef.current) {
      mapRef.current.animateToRegion(coords, 300);
    }
  };

  const panToCoordinate = (name: string, latitude: number, longitude: number) => {
    setActiveRegion(name);
    setSearchQuery(name);
    setShowSuggestions(false);
    Keyboard.dismiss();
    const region = { latitude, longitude, latitudeDelta: 0.3, longitudeDelta: 0.3 };
    setMapRegion(region);
    if (mapRef.current) {
      mapRef.current.animateToRegion(region, 500);
    }
  };

  const handleSearchSubmit = async () => {
    const query = searchQuery.trim();
    if (query.length === 0) {
      selectRegion("All");
      return;
    }
    // 1) Try exact region match first
    const regionMatch = availableRegions.find(
      (r) => r.toLowerCase() === query.toLowerCase()
    );
    if (regionMatch) {
      selectRegion(regionMatch);
      return;
    }
    // 2) Try partial region match
    const partialMatch = availableRegions.find((r) =>
      r.toLowerCase().includes(query.toLowerCase())
    );
    if (partialMatch) {
      selectRegion(partialMatch);
      return;
    }
    // 3) Geocode via Nominatim (works on web + native)
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query + ", France")}&format=json&limit=1&accept-language=fr`;
      const res = await fetch(url, {
        headers: { "User-Agent": "AgriMent/1.0" },
      });
      const data = await res.json();
      if (data.length > 0) {
        const { lat, lon, display_name } = data[0];
        const name = display_name.split(",")[0];
        panToCoordinate(name, parseFloat(lat), parseFloat(lon));
      }
    } catch {
      // Geocoding failed — silently ignore
    }
  };

  // FIX: Normalize risk level to lowercase before comparison to handle
  // inconsistent casing from database or API
  const filteredDetections = detections.filter((d) => {
    if (riskFilter !== "all") {
      const detectionRisk = (d.risk || "").toLowerCase();
      if (detectionRisk !== riskFilter) return false;
    }
    return true;
  });

  const allDetections = filteredDetections.map((d, i) => {
    if (d.latitude != null && d.longitude != null) {
      return d;
    }
    const regionCoords = getRegionCoords(d.region);
    const offsetLat = Math.sin(i * 2.7 + 1.3) * 0.08;
    const offsetLng = Math.cos(i * 3.1 + 0.7) * 0.08;
    return {
      ...d,
      latitude: regionCoords.latitude + offsetLat,
      longitude: regionCoords.longitude + offsetLng,
    };
  });

  const alertCount = allDetections.filter((d) => d.notified_count > 0).length;

  // Once the map is ready and markers are loaded, zoom to where they actually
  // are. Without this the map stays centered on France while detections with
  // GPS coordinates far from it (e.g. real user location) render off-screen.
  useEffect(() => {
    if (!mapReady || !mapRef.current || allDetections.length === 0 || hasFitRef.current) {
      return;
    }
    hasFitRef.current = true;
    const coords = allDetections.map((d) => {
      const rc = getRegionCoords(d.region);
      return {
        latitude: d.latitude ?? rc.latitude,
        longitude: d.longitude ?? rc.longitude,
      };
    });
    if (coords.length === 1) {
      mapRef.current.animateToRegion(
        { ...coords[0], latitudeDelta: 1.2, longitudeDelta: 1.2 },
        500
      );
    } else {
      mapRef.current.fitToCoordinates(coords, {
        edgePadding: { top: 80, right: 40, bottom: 100, left: 40 },
        animated: true,
      });
    }
  }, [mapReady, allDetections, mapRegion]);

  // When navigated with highlightedDetectionId (e.g. after sending an alert),
  // zoom to that specific detection and highlight it on the map.
  useEffect(() => {
    if (!mapReady || !mapRef.current || !route?.params?.highlightedDetectionId) return;
    const highlighted = allDetections.find(d => d.id === route.params.highlightedDetectionId);
    if (!highlighted) return;
    const rc = getRegionCoords(highlighted.region);
    const lat = highlighted.latitude ?? rc.latitude;
    const lng = highlighted.longitude ?? rc.longitude;
    mapRef.current.animateToRegion(
      { latitude: lat, longitude: lng, latitudeDelta: 0.5, longitudeDelta: 0.5 },
      600
    );
  }, [mapReady, allDetections, route?.params?.highlightedDetectionId]);

  return (
    <View style={styles.container}>
      <Header
        title="Pest Map"
        subtitle={`${allDetections.length} detections - ${activeRegion === "All" ? "All regions" : activeRegion}`}
        showBack
        onBack={() => navigation.goBack()}
      />

      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={18} color="#757575" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search region or city..."
            placeholderTextColor="#BDBDBD"
            value={searchQuery}
            onChangeText={(text) => {
              setSearchQuery(text);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onSubmitEditing={handleSearchSubmit}
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => {
              setSearchQuery("");
              setShowSuggestions(false);
              selectRegion("All");
            }}>
              <Ionicons name="close-circle" size={18} color="#BDBDBD" />
            </TouchableOpacity>
          )}
        </View>

        {showSuggestions && (
          <View style={styles.suggestions}>
            <TouchableOpacity
              style={[styles.suggestionItem, activeRegion === "All" && styles.suggestionItemActive]}
              onPress={() => selectRegion("All")}
            >
              <Ionicons name="globe-outline" size={16} color={activeRegion === "All" ? "#2E7D32" : "#757575"} />
              <Text style={[styles.suggestionText, activeRegion === "All" && styles.suggestionTextActive]}>
                All regions
              </Text>
              {activeRegion === "All" && <Ionicons name="checkmark" size={16} color="#2E7D32" />}
            </TouchableOpacity>
            {filteredRegions.map((r) => (
              <TouchableOpacity
                key={r}
                style={[styles.suggestionItem, r === activeRegion && styles.suggestionItemActive]}
                onPress={() => selectRegion(r)}
              >
                <Ionicons name="location-outline" size={16} color={r === activeRegion ? "#2E7D32" : "#757575"} />
                <Text style={[styles.suggestionText, r === activeRegion && styles.suggestionTextActive]}>
                  {r}
                </Text>
                {r === activeRegion && <Ionicons name="checkmark" size={16} color="#2E7D32" />}
              </TouchableOpacity>
            ))}
            {geoSuggestions.length > 0 && (
              <>
                <View style={styles.suggestionDivider}>
                  <Text style={styles.suggestionDividerText}>Places</Text>
                </View>
                {geoSuggestions.map((g, i) => (
                  <TouchableOpacity
                    key={`${g.name}-${i}`}
                    style={styles.suggestionItem}
                    onPress={() => panToCoordinate(g.name, g.latitude, g.longitude)}
                  >
                    <Ionicons name="map-outline" size={16} color="#1976D2" />
                    <Text style={[styles.suggestionText, { color: "#1976D2" }]}>
                      {g.name}
                    </Text>
                    <Ionicons name="arrow-forward" size={14} color="#1976D2" />
                  </TouchableOpacity>
                ))}
              </>
            )}
            {geoLoading && searchQuery.length >= 2 && (
              <View style={styles.suggestionItem}>
                <ActivityIndicator size="small" color="#757575" />
                <Text style={[styles.suggestionText, { color: "#757575", marginLeft: 8 }]}>
                  Searching...
                </Text>
              </View>
            )}
            {filteredRegions.length === 0 && geoSuggestions.length === 0 && !geoLoading && searchQuery.length > 0 && (
              <View style={styles.suggestionItem}>
                <Ionicons name="search-outline" size={16} color="#BDBDBD" />
                <Text style={[styles.suggestionText, { color: "#BDBDBD" }]}>
                  No results for "{searchQuery}"
                </Text>
              </View>
            )}
          </View>
        )}
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.filterBar}
        contentContainerStyle={styles.filterContent}
      >
        {RISK_FILTERS.map((f) => {
          const isActive = riskFilter === f.key;
          const count = f.key === "all"
            ? detections.length
            : detections.filter((d) => (d.risk || "").toLowerCase() === f.key).length;
          return (
            <TouchableOpacity
              key={f.key}
              style={[styles.filterChip, isActive && { backgroundColor: f.color, borderColor: f.color }]}
              onPress={() => setRiskFilter(f.key)}
            >
              {f.key !== "all" && (
                <View style={[styles.filterDot, { backgroundColor: isActive ? "#FFF" : f.color }]} />
              )}
              <Text style={[styles.filterLabel, isActive && { color: "#FFF" }]}>
                {f.label}
              </Text>
              <View style={[styles.filterCount, { backgroundColor: isActive ? "rgba(255,255,255,0.3)" : "#F0F0F0" }]}>
                <Text style={[styles.filterCountText, isActive && { color: "#FFF" }]}>{count}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#2E7D32" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      ) : (
        <View style={styles.mapContainer}>
          <MapContentView
            detections={allDetections}
            mapRegion={mapRegion}
            onMapReady={() => setMapReady(true)}
            navigation={navigation}
            mapRef={mapRef}
          />

          <View style={styles.mapLegend}>
            {["low", "medium", "high", "critical"].map((risk) => {
              const config = getRiskConfig(risk);
              return (
                <View key={risk} style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: config.color }]} />
                  <Text style={styles.legendText}>{config.label}</Text>
                </View>
              );
            })}
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: "#F44336", width: 14, height: 14, borderRadius: 7 }]} />
              <Text style={styles.legendText}>Alert</Text>
            </View>
          </View>

          {alertCount > 0 && (
            <TouchableOpacity
              style={styles.alertsButton}
              onPress={() => navigation.navigate("Notifications")}
            >
              <View style={styles.alertsButtonIcon}>
                <Ionicons name="notifications" size={20} color="#FFF" />
              </View>
              <View style={styles.alertsButtonText}>
                <Text style={styles.alertsButtonCount}>{alertCount}</Text>
                <Text style={styles.alertsButtonLabel}>Alerts</Text>
              </View>
            </TouchableOpacity>
          )}

          {allDetections.length === 0 && !loading && Platform.OS !== "web" && (
            <View style={styles.noDataOverlay}>
              <Ionicons name="bug-outline" size={24} color="#757575" />
              <Text style={styles.noDataText}>
                No detections for this filter.
              </Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8F9FA",
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
    backgroundColor: "#F8F9FA",
    zIndex: 10,
  },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
    borderWidth: 1.5,
    borderColor: "#E0E0E0",
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: "#212121",
    paddingVertical: 2,
  },
  suggestions: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    marginTop: 4,
    borderWidth: 1,
    borderColor: "#E0E0E0",
    maxHeight: 220,
    overflow: "hidden",
  },
  suggestionItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: "#F0F0F0",
  },
  suggestionItemActive: {
    backgroundColor: "#E8F5E9",
  },
  suggestionText: {
    flex: 1,
    fontSize: 14,
    color: "#424242",
  },
  suggestionTextActive: {
    color: "#2E7D32",
    fontWeight: "700",
  },
  suggestionDivider: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    backgroundColor: "#F5F5F5",
    borderTopWidth: 1,
    borderTopColor: "#E0E0E0",
  },
  suggestionDividerText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#9E9E9E",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  filterBar: {
    maxHeight: 48,
    backgroundColor: "#F8F9FA",
  },
  filterContent: {
    paddingHorizontal: 16,
    paddingBottom: 8,
    gap: 8,
  },
  filterChip: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: "#E0E0E0",
    backgroundColor: "#FFF",
    gap: 6,
  },
  filterDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  filterLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#424242",
  },
  filterCount: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  filterCountText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#757575",
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: "#757575",
  },
  mapContainer: {
    flex: 1,
  },
  mapLegend: {
    position: "absolute",
    bottom: 16,
    left: 16,
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 12,
    padding: 10,
    flexDirection: "row",
    gap: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: 10,
    fontWeight: "600",
    color: "#616161",
  },
  alertsButton: {
    position: "absolute",
    bottom: 16,
    right: 16,
    backgroundColor: "#F44336",
    borderRadius: 16,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
    shadowColor: "#F44336",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  alertsButtonIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.25)",
    alignItems: "center",
    justifyContent: "center",
  },
  alertsButtonText: {
    alignItems: "center",
  },
  alertsButtonCount: {
    fontSize: 16,
    fontWeight: "800",
    color: "#FFF",
  },
  alertsButtonLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: "rgba(255,255,255,0.85)",
  },
  noDataOverlay: {
    position: "absolute",
    bottom: 16,
    left: 16,
    right: 16,
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  noDataText: {
    fontSize: 13,
    color: "#757575",
    flex: 1,
  },
});
