import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import { Header } from "../components";
import { useNavigation } from "@react-navigation/native";

const FEATURES = [
  {
    icon: "camera" as const,
    title: "Detect",
    subtitle: "Photograph an insect",
    screen: "Detect",
    color: "#2E7D32",
  },
  {
    icon: "map" as const,
    title: "Pest Map",
    subtitle: "See nearby alerts",
    screen: "Map",
    color: "#FF5722",
  },
  {
    icon: "notifications" as const,
    title: "Alerts",
    subtitle: "Regional notifications",
    screen: "Notifications",
    color: "#FF9800",
  },
  {
    icon: "time" as const,
    title: "History",
    subtitle: "Your past detections",
    screen: "History",
    color: "#2196F3",
  },
  {
    icon: "person" as const,
    title: "Profile",
    subtitle: "Manage your account",
    screen: "Profile",
    color: "#9C27B0",
  },
];

export default function HomeScreen() {
  const { user } = useAuth();
  const navigation = useNavigation<any>();

  return (
    <View style={styles.container}>
      <Header
        title="AgriMent"
        subtitle={`Welcome, ${user?.name || "Farmer"}`}
      />

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
      >
        <View style={styles.greetingCard}>
          <View style={styles.greetingContent}>
            <Text style={styles.greetingTitle}>Ready to detect?</Text>
            <Text style={styles.greetingText}>
              Point your camera at any insect and let the AI
              identify it instantly.
            </Text>
          </View>
          <TouchableOpacity
            style={styles.detectButton}
            onPress={() => navigation.navigate("Detect")}
          >
            <Ionicons name="camera" size={28} color="#FFFFFF" />
          </TouchableOpacity>
        </View>

        <Text style={styles.sectionTitle}>Quick Access</Text>

        <View style={styles.featuresGrid}>
          {FEATURES.map((feature) => (
            <TouchableOpacity
              key={feature.title}
              style={styles.featureCard}
              onPress={() => navigation.navigate(feature.screen)}
              activeOpacity={0.8}
            >
              <View
                style={[
                  styles.featureIcon,
                  { backgroundColor: `${feature.color}15` },
                ]}
              >
                <Ionicons
                  name={feature.icon}
                  size={28}
                  color={feature.color}
                />
              </View>
              <Text style={styles.featureTitle}>{feature.title}</Text>
              <Text style={styles.featureSubtitle}>{feature.subtitle}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.regionCard}>
          <Ionicons name="location" size={20} color="#2E7D32" />
          <View style={styles.regionInfo}>
            <Text style={styles.regionLabel}>Your Region</Text>
            <Text style={styles.regionValue}>{user?.region || "N/A"}</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8F9FA",
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  greetingCard: {
    flexDirection: "row",
    backgroundColor: "#2E7D32",
    borderRadius: 20,
    padding: 24,
    marginBottom: 28,
    alignItems: "center",
  },
  greetingContent: {
    flex: 1,
  },
  greetingTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#FFFFFF",
    marginBottom: 6,
  },
  greetingText: {
    fontSize: 14,
    color: "rgba(255,255,255,0.85)",
    lineHeight: 20,
  },
  detectButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#212121",
    marginBottom: 16,
  },
  featuresGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  featureCard: {
    width: "48%",
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  featureIcon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  featureTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#212121",
    marginBottom: 4,
  },
  featureSubtitle: {
    fontSize: 12,
    color: "#757575",
    lineHeight: 16,
  },
  regionCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#E8F5E9",
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  regionInfo: {
    flex: 1,
  },
  regionLabel: {
    fontSize: 12,
    color: "#757575",
    fontWeight: "500",
  },
  regionValue: {
    fontSize: 16,
    fontWeight: "700",
    color: "#2E7D32",
  },
});
