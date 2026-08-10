import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Detection } from "../types";
import { getRiskColor, getRiskLabel } from "../utils/theme";

export interface MapContentViewProps {
  detections: Detection[];
  mapRegion: any;
  onMapReady: () => void;
  navigation: any;
  mapRef: any;
}

export function MapContentView({
  detections,
  navigation,
}: MapContentViewProps) {
  return (
    <View style={styles.webMapContainer}>
      <View style={styles.webMapPlaceholder}>
        <Ionicons name="map-outline" size={48} color="#BDBDBD" />
        <Text style={styles.webMapText}>Map available on mobile</Text>
      </View>
      <View style={styles.detectionsList}>
        {detections.map((d) => {
          const isAlerted = d.notified_count > 0;
          return (
            <TouchableOpacity
              key={d.id}
              style={styles.detectionListItem}
              onPress={() => navigation.navigate("Result", { detection: d })}
            >
              <View
                style={[
                  styles.riskDot,
                  { backgroundColor: getRiskColor(d.risk) },
                ]}
              />
              <View style={styles.detectionListInfo}>
                <Text style={styles.detectionListSpecies}>{d.species}</Text>
                <Text style={styles.detectionListMeta}>
                  {getRiskLabel(d.risk)} - {d.region} -{" "}
                  {new Date(d.created_at).toLocaleDateString("en-US")}
                  {isAlerted ? " - Alert sent" : ""}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#BDBDBD" />
            </TouchableOpacity>
          );
        })}
        {detections.length === 0 && (
          <Text style={styles.emptyText}>No detections for this filter.</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  webMapContainer: {
    flex: 1,
    padding: 16,
  },
  webMapPlaceholder: {
    height: 180,
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  webMapText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#424242",
    marginTop: 12,
  },
  detectionsList: {
    flex: 1,
  },
  detectionListItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFF",
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  riskDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  detectionListInfo: {
    flex: 1,
  },
  detectionListSpecies: {
    fontSize: 15,
    fontWeight: "600",
    color: "#212121",
  },
  detectionListMeta: {
    fontSize: 12,
    color: "#9E9E9E",
  },
  emptyText: {
    fontSize: 14,
    color: "#9E9E9E",
    textAlign: "center",
    marginTop: 24,
  },
});
