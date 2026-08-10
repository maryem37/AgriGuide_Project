import React from "react";
import { View, Text, Image, StyleSheet, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Detection } from "../types";
import { API_IMAGE_URL } from "../utils/config";
import { getRiskConfig } from "../utils/theme";

interface DetectionCardProps {
  detection: Detection;
  onPress?: () => void;
}

export function DetectionCard({ detection, onPress }: DetectionCardProps) {
  const riskConfig = getRiskConfig(detection.risk);
  const confidencePercent = Math.round(detection.confidence * 100);
  const imageUrl = `${API_IMAGE_URL}${detection.image_url}`;

  return (
    <TouchableOpacity
      style={styles.container}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <View style={styles.imageContainer}>
        {detection.image_url ? (
          <Image source={{ uri: imageUrl }} style={styles.image} />
        ) : (
          <Ionicons name="bug" size={32} color="#2E7D32" />
        )}
      </View>

      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.species} numberOfLines={1}>
            {detection.species}
          </Text>
          <View style={[styles.riskBadge, { backgroundColor: riskConfig.color }]}>
            <Text style={styles.riskText}>{detection.risk.toUpperCase()}</Text>
          </View>
        </View>

        <Text style={styles.scientific}>{detection.scientific_name}</Text>

        <View style={styles.footer}>
          <View style={styles.confidenceContainer}>
            <View style={styles.confidenceBar}>
              <View
                style={[
                  styles.confidenceFill,
                  { width: `${confidencePercent}%`, backgroundColor: riskConfig.color },
                ]}
              />
            </View>
            <Text style={styles.confidenceText}>{confidencePercent}%</Text>
          </View>

          <Text style={styles.date}>
            {new Date(detection.created_at).toLocaleDateString("fr-FR")}
          </Text>
        </View>

        {detection.notified_count > 0 && (
          <View style={styles.notifiedRow}>
            <Ionicons name="notifications" size={14} color="#4CAF50" />
            <Text style={styles.notifiedText}>
              {detection.notified_count} farmers notified
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  imageContainer: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: "#E8F5E9",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
    overflow: "hidden",
  },
  image: {
    width: "100%",
    height: "100%",
  },
  content: { flex: 1 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  species: {
    fontSize: 16,
    fontWeight: "700",
    color: "#212121",
    flex: 1,
    marginRight: 8,
  },
  riskBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  riskText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
  },
  scientific: {
    fontSize: 13,
    fontStyle: "italic",
    color: "#757575",
    marginBottom: 8,
  },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  confidenceContainer: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
    marginRight: 12,
  },
  confidenceBar: {
    flex: 1,
    height: 6,
    backgroundColor: "#F0F0F0",
    borderRadius: 3,
    marginRight: 8,
    overflow: "hidden",
  },
  confidenceFill: {
    height: "100%",
    borderRadius: 3,
  },
  confidenceText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#757575",
    minWidth: 36,
  },
  date: {
    fontSize: 12,
    color: "#757575",
  },
  notifiedRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
    gap: 4,
  },
  notifiedText: {
    fontSize: 12,
    color: "#4CAF50",
    fontWeight: "500",
  },
});
