import React from "react";
import { View, StyleSheet } from "react-native";
import MapView, { Marker } from "react-native-maps";
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
  mapRegion,
  onMapReady,
  navigation,
  mapRef,
}: MapContentViewProps) {
  return (
    <MapView
      ref={mapRef}
      style={styles.map}
      initialRegion={mapRegion}
      showsUserLocation
      showsMyLocationButton
      onMapReady={onMapReady}
    >
      {detections.map((d) => {
        const isAlerted = d.notified_count > 0;
        // FIX: Always use risk-based color. Alerted markers are distinguished
        // by size/style, not by overriding the color to red.
        const markerColor = getRiskColor(d.risk);
        return (
          <Marker
            key={d.id}
            coordinate={{ latitude: d.latitude!, longitude: d.longitude! }}
            title={isAlerted ? `Alert: ${d.species}` : d.species}
            description={`${getRiskLabel(d.risk)} - ${d.region}${isAlerted ? " - Alert sent" : ""}`}
            onCalloutPress={() =>
              navigation.navigate("Result", { detection: d })
            }
          >
            <View style={styles.markerContainer}>
              <View
                style={[
                  styles.markerDot,
                  { backgroundColor: markerColor },
                  isAlerted && styles.markerDotAlerted,
                ]}
              />
              {isAlerted && (
                <View style={styles.alertIndicator}>
                  <View style={styles.alertDot} />
                </View>
              )}
            </View>
          </Marker>
        );
      })}
    </MapView>
  );
}

const styles = StyleSheet.create({
  map: {
    flex: 1,
  },
  markerContainer: {
    alignItems: "center",
    justifyContent: "center",
  },
  markerDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 3,
    borderColor: "#FFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
  },
  markerDotAlerted: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 4,
  },
  alertIndicator: {
    position: "absolute",
    top: -4,
    right: -4,
    backgroundColor: "#FFF",
    borderRadius: 8,
    padding: 2,
  },
  alertDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#F44336",
  },
});
