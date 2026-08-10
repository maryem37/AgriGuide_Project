import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Alert,
  Dimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Header, PrimaryButton, RecommendationBox } from "../components";
import { Detection } from "../types";
import { API_IMAGE_URL } from "../utils/config";
import { detectionService } from "../services/detection";
import { showDemoAlertNotification } from "../utils/notifications";
import { getRiskConfig } from "../utils/theme";

export default function ResultScreen({ route, navigation }: any) {
  const detection: Detection = route.params.detection;
  const riskConfig = getRiskConfig(detection.risk);
  const confidencePercent = Math.round(detection.confidence * 100);
  const imageUrl = `${API_IMAGE_URL}${detection.image_url}`;
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(detection.notified_count > 0);
  const [notifiedCount, setNotifiedCount] = useState(detection.notified_count);

  const handleSendAlert = async () => {
    Alert.alert(
      "Send Alert to Region",
      `Send an alert to all farmers in ${detection.region}?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Send",
          style: "destructive",
          onPress: async () => {
            setSending(true);
            try {
              const result = await detectionService.sendAlert(detection.id);
              setSent(true);
              setNotifiedCount(result.notified_count);
              await showDemoAlertNotification({
                detectionId: detection.id,
                species: detection.species,
                region: detection.region,
              });
              Alert.alert(
                "Alert Sent",
                `${result.notified_count} farmers in ${detection.region} have been alerted.`
              );
              navigation.replace("Map", {
                refreshKey: Date.now(),
                highlightedDetectionId: detection.id,
                highlightedRegion: detection.region,
              });
            } catch (err: any) {
              Alert.alert("Error", err.response?.data?.detail || "Failed to send");
            } finally {
              setSending(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <Header
        title="Result"
        showBack
        onBack={() => navigation.goBack()}
      />

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.imageSection}>
          <Image source={{ uri: imageUrl }} style={styles.resultImage} />
          <View style={[styles.riskBadge, { backgroundColor: riskConfig.color }]}>
            <Ionicons name={riskConfig.icon} size={14} color="#FFF" />
            <Text style={styles.riskBadgeText}>{riskConfig.label}</Text>
          </View>
        </View>

        <View style={styles.speciesSection}>
          <Text style={styles.species}>{detection.species}</Text>
          <Text style={styles.scientific}>{detection.scientific_name}</Text>
          <View style={[styles.regionBadge, { backgroundColor: riskConfig.bg }]}>
            <Ionicons name="location" size={12} color={riskConfig.color} />
            <Text style={[styles.regionText, { color: riskConfig.color }]}>
              {detection.region}
            </Text>
          </View>
        </View>

        <View style={styles.statsRow}>
          <View style={[styles.statCard, { backgroundColor: riskConfig.bg }]}>
            <Ionicons name={riskConfig.icon} size={24} color={riskConfig.color} />
            <Text style={[styles.statValue, { color: riskConfig.color }]}>
              {riskConfig.label}
            </Text>
            <Text style={styles.statLabel}>Risk Level</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: "#E3F2FD" }]}>
            <Ionicons name="analytics" size={24} color="#1976D2" />
            <Text style={[styles.statValue, { color: "#1976D2" }]}>
              {confidencePercent}%
            </Text>
            <Text style={styles.statLabel}>Confidence</Text>
          </View>
        </View>

        <View style={styles.confidenceSection}>
          <View style={styles.confidenceHeader}>
            <Text style={styles.confidenceLabel}>Confidence Score</Text>
            <Text style={[styles.confidenceValue, { color: riskConfig.color }]}>
              {confidencePercent}%
            </Text>
          </View>
          <View style={styles.confidenceBarBg}>
            <View
              style={[
                styles.confidenceBarFill,
                { width: `${confidencePercent}%`, backgroundColor: riskConfig.color },
              ]}
            />
          </View>
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIcon, { backgroundColor: "#E3F2FD" }]}>
              <Ionicons name="document-text" size={18} color="#1976D2" />
            </View>
            <Text style={styles.cardTitle}>Description</Text>
          </View>
          <RecommendationBox title={detection.description} color="#1976D2" />
        </View>

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIcon, { backgroundColor: "#FFF3E0" }]}>
              <Ionicons name="bulb" size={18} color="#FF9800" />
            </View>
            <Text style={styles.cardTitle}>Recommendation</Text>
          </View>
          <RecommendationBox title={detection.recommendation} color="#FF9800" />
        </View>

        <View style={styles.alertSection}>
          {sent ? (
            <View style={styles.alertSentCard}>
              <View style={styles.alertSentIcon}>
                <Ionicons name="checkmark-circle" size={28} color="#4CAF50" />
              </View>
              <Text style={styles.alertSentTitle}>Region Alerted</Text>
              <Text style={styles.alertSentText}>
                {notifiedCount} farmers in {detection.region} have been
                informed of this detection.
              </Text>
            </View>
          ) : (
            <View style={styles.alertActionCard}>
              <View style={styles.alertActionHeader}>
                <Ionicons name="notifications-outline" size={22} color="#2E7D32" />
                <Text style={styles.alertActionTitle}>Regional Alert</Text>
              </View>
              <Text style={styles.alertActionText}>
                Send an alert to all farmers in {detection.region} regarding this
                detection of {detection.species}.
              </Text>
              <PrimaryButton
                title="Send Alert to Region"
                onPress={handleSendAlert}
                loading={sending}
                variant="primary"
                size="md"
                style={styles.alertButton}
              />
            </View>
          )}
        </View>

        <PrimaryButton
          title="Finish"
          onPress={() => navigation.navigate("HomeTab")}
          variant="outline"
          size="lg"
          style={styles.doneButton}
        />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F7FA" },
  content: { flex: 1 },
  scrollContent: { paddingBottom: 40 },
  imageSection: { height: 240, backgroundColor: "#FFF", position: "relative" },
  resultImage: { width: "100%", height: "100%" },
  riskBadge: {
    position: "absolute", top: 16, right: 16,
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, gap: 5,
  },
  riskBadgeText: { color: "#FFF", fontSize: 12, fontWeight: "700" },
  speciesSection: {
    alignItems: "center", paddingVertical: 20, backgroundColor: "#FFF",
    borderBottomLeftRadius: 24, borderBottomRightRadius: 24, marginBottom: 16,
  },
  species: { fontSize: 24, fontWeight: "800", color: "#212121", textAlign: "center" },
  scientific: { fontSize: 15, fontStyle: "italic", color: "#9E9E9E", marginTop: 4, marginBottom: 12 },
  regionBadge: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, gap: 4,
  },
  regionText: { fontSize: 12, fontWeight: "600" },
  statsRow: { flexDirection: "row", paddingHorizontal: 16, gap: 12, marginBottom: 16 },
  statCard: { flex: 1, alignItems: "center", padding: 16, borderRadius: 16, gap: 4 },
  statValue: { fontSize: 18, fontWeight: "800" },
  statLabel: { fontSize: 11, fontWeight: "500", color: "#9E9E9E", textTransform: "uppercase", letterSpacing: 0.5 },
  confidenceSection: { marginHorizontal: 16, marginBottom: 16, backgroundColor: "#FFF", borderRadius: 16, padding: 16 },
  confidenceHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  confidenceLabel: { fontSize: 14, fontWeight: "600", color: "#616161" },
  confidenceValue: { fontSize: 16, fontWeight: "800" },
  confidenceBarBg: { height: 8, backgroundColor: "#F0F0F0", borderRadius: 4, overflow: "hidden" },
  confidenceBarFill: { height: "100%", borderRadius: 4 },
  card: { marginHorizontal: 16, marginBottom: 12, backgroundColor: "#FFF", borderRadius: 16, padding: 16 },
  cardHeader: { flexDirection: "row", alignItems: "center", marginBottom: 12, gap: 10 },
  cardIcon: { width: 32, height: 32, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontSize: 16, fontWeight: "700", color: "#212121" },
  alertSection: { marginHorizontal: 16, marginBottom: 16 },
  alertSentCard: { backgroundColor: "#E8F5E9", borderRadius: 16, padding: 20, alignItems: "center" },
  alertSentIcon: { marginBottom: 8 },
  alertSentTitle: { fontSize: 17, fontWeight: "700", color: "#2E7D32", marginBottom: 6 },
  alertSentText: { fontSize: 13, color: "#558B2F", textAlign: "center", lineHeight: 18 },
  alertActionCard: {
    backgroundColor: "#FFF", borderRadius: 16, padding: 20,
    borderWidth: 1.5, borderColor: "#C8E6C9", borderStyle: "dashed",
  },
  alertActionHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  alertActionTitle: { fontSize: 17, fontWeight: "700", color: "#2E7D32" },
  alertActionText: { fontSize: 13, color: "#757575", lineHeight: 20, marginBottom: 16 },
  alertButton: { width: "100%" },
  doneButton: { marginHorizontal: 16, width: "auto" },
});
