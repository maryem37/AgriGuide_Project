import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Header, RecommendationBox } from "../components";
import { Detection, Notification } from "../types";
import { API_IMAGE_URL } from "../utils/config";
import { detectionService } from "../services/detection";
import { getRiskConfig } from "../utils/theme";

function getTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function NotificationDetailScreen({ route, navigation }: any) {
  const notification: Notification = route.params.notification;
  const [detection, setDetection] = useState<Detection | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (notification.detection_id) {
      detectionService
        .getDetection(notification.detection_id)
        .then(setDetection)
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [notification.detection_id]);

  const riskConfig = detection
      ? getRiskConfig(detection.risk)
      : getRiskConfig("low");
  return (
    <View style={styles.container}>
      <Header
        title="Alert Details"
        showBack
        onBack={() => navigation.goBack()}
      />

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.topBanner}>
          <Ionicons name="notifications" size={32} color="#FF9800" />
          <Text style={styles.bannerTitle}>{notification.title}</Text>
          <Text style={styles.bannerTime}>{getTimeAgo(notification.created_at)}</Text>
        </View>

        <View style={styles.alertCard}>
          <View style={styles.alertRow}>
            <Ionicons name="location" size={16} color="#757575" />
            <Text style={styles.alertRegion}>{notification.region}</Text>
          </View>
          <View style={styles.alertRow}>
            <Ionicons name="bug" size={16} color="#757575" />
            <Text style={styles.alertSpecies}>{notification.species}</Text>
          </View>
        </View>

        <View style={styles.messageCard}>
          <Text style={styles.messageTitle}>Message</Text>
          <Text style={styles.messageText}>{notification.message}</Text>
        </View>

        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#2E7D32" />
            <Text style={styles.loadingText}>Loading details...</Text>
          </View>
        ) : detection ? (
          <>
            <View style={styles.detectionHeader}>
              <Ionicons name="analytics" size={18} color="#2E7D32" />
              <Text style={styles.detectionTitle}>Detection Details</Text>
            </View>

            <View style={styles.imageCard}>
              <Image
                source={{ uri: `${API_IMAGE_URL}${detection.image_url}` }}
                style={styles.detectionImage}
              />
              <View style={[styles.riskBadge, { backgroundColor: riskConfig.color }]}>
                <Ionicons name={riskConfig.icon} size={12} color="#FFF" />
                <Text style={styles.riskBadgeText}>{riskConfig.label}</Text>
              </View>
            </View>

            <View style={styles.speciesCard}>
              <Text style={styles.species}>{detection.species}</Text>
              <Text style={styles.scientific}>{detection.scientific_name}</Text>
            </View>

            <View style={styles.statsRow}>
              <View style={[styles.statItem, { backgroundColor: riskConfig.bg }]}>
                <Text style={[styles.statValue, { color: riskConfig.color }]}>
                  {riskConfig.label}
                </Text>
                <Text style={styles.statLabel}>Risk Level</Text>
              </View>
              <View style={[styles.statItem, { backgroundColor: "#E3F2FD" }]}>
                <Text style={[styles.statValue, { color: "#1976D2" }]}>
                  {Math.round(detection.confidence * 100)}%
                </Text>
                <Text style={styles.statLabel}>Confidence</Text>
              </View>
            </View>

            <View style={styles.infoCard}>
              <View style={styles.infoHeader}>
                <View style={[styles.infoIcon, { backgroundColor: "#E3F2FD" }]}>
                  <Ionicons name="document-text" size={16} color="#1976D2" />
                </View>
                <Text style={styles.infoTitle}>Description</Text>
              </View>
              <RecommendationBox title={detection.description || ""} color="#1976D2" />
            </View>

            <View style={styles.infoCard}>
              <View style={styles.infoHeader}>
                <View style={[styles.infoIcon, { backgroundColor: "#FFF3E0" }]}>
                  <Ionicons name="bulb" size={16} color="#FF9800" />
                </View>
                <Text style={styles.infoTitle}>Recommended Actions</Text>
              </View>
              <RecommendationBox title={detection.recommendation || ""} color="#FF9800" />
            </View>

            <View style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>Summary</Text>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Region</Text>
                <Text style={styles.summaryValue}>{detection.region}</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Notified by</Text>
                <Text style={styles.summaryValue}>
                  {detection.notified_count} farmer(s) notified
                </Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Date</Text>
                <Text style={styles.summaryValue}>
                  {new Date(detection.created_at).toLocaleDateString("en-US", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </Text>
              </View>
            </View>
          </>
        ) : (
          <View style={styles.emptyCard}>
            <Ionicons name="information-circle" size={32} color="#9E9E9E" />
            <Text style={styles.emptyText}>
              Detection details are not available for this alert.
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F7FA",
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 40,
  },
  topBanner: {
    backgroundColor: "#FFF8E1",
    padding: 20,
    alignItems: "center",
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    marginBottom: 16,
  },
  bannerTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#212121",
    marginTop: 8,
  },
  bannerTime: {
    fontSize: 12,
    color: "#9E9E9E",
    marginTop: 4,
  },
  alertCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    gap: 8,
    marginBottom: 12,
  },
  alertRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  alertRegion: {
    fontSize: 14,
    fontWeight: "600",
    color: "#424242",
  },
  alertSpecies: {
    fontSize: 14,
    fontWeight: "600",
    color: "#424242",
  },
  messageCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  messageTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#212121",
    marginBottom: 8,
  },
  messageText: {
    fontSize: 13,
    color: "#616161",
    lineHeight: 20,
  },
  loadingContainer: {
    alignItems: "center",
    padding: 40,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: "#757575",
  },
  detectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: 16,
    marginBottom: 12,
  },
  detectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#2E7D32",
  },
  imageCard: {
    marginHorizontal: 16,
    height: 200,
    borderRadius: 16,
    overflow: "hidden",
    marginBottom: 12,
    position: "relative",
  },
  detectionImage: {
    width: "100%",
    height: "100%",
  },
  riskBadge: {
    position: "absolute",
    top: 12,
    right: 12,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  riskBadgeText: {
    color: "#FFF",
    fontSize: 11,
    fontWeight: "700",
  },
  speciesCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
    marginBottom: 12,
  },
  species: {
    fontSize: 20,
    fontWeight: "800",
    color: "#212121",
  },
  scientific: {
    fontSize: 14,
    fontStyle: "italic",
    color: "#9E9E9E",
    marginTop: 4,
  },
  statsRow: {
    flexDirection: "row",
    marginHorizontal: 16,
    gap: 12,
    marginBottom: 12,
  },
  statItem: {
    flex: 1,
    alignItems: "center",
    padding: 14,
    borderRadius: 12,
  },
  statValue: {
    fontSize: 15,
    fontWeight: "800",
  },
  statLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: "#9E9E9E",
    textTransform: "uppercase",
    marginTop: 4,
  },
  infoCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  infoHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  infoIcon: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  infoTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#212121",
  },
  summaryCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  summaryTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#212121",
    marginBottom: 12,
  },
  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: "#F5F5F5",
  },
  summaryLabel: {
    fontSize: 13,
    color: "#9E9E9E",
  },
  summaryValue: {
    fontSize: 13,
    fontWeight: "600",
    color: "#424242",
  },
  emptyCard: {
    marginHorizontal: 16,
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 32,
    alignItems: "center",
  },
  emptyText: {
    marginTop: 12,
    fontSize: 14,
    color: "#9E9E9E",
    textAlign: "center",
  },
});
