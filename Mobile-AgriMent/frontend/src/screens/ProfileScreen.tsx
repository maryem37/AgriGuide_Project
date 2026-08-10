import React from "react";
import { View, Text, StyleSheet, Alert } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Header, Card, PrimaryButton } from "../components";
import { useAuth } from "../context/AuthContext";

export default function ProfileScreen({ navigation }: any) {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert("Logout", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      { text: "Logout", style: "destructive", onPress: async () => { await logout(); } },
    ]);
  };

  return (
    <View style={styles.container}>
      <Header title="Profile" showBack onBack={() => navigation.goBack()} />
      <View style={styles.content}>
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.name?.charAt(0).toUpperCase() || "A"}</Text>
          </View>
          <Text style={styles.name}>{user?.name || "Farmer"}</Text>
          <Text style={styles.email}>{user?.email || ""}</Text>
        </View>
        <Card>
          <View style={styles.infoRow}>
            <Ionicons name="person-outline" size={20} color="#757575" />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Full Name</Text>
              <Text style={styles.infoValue}>{user?.name || "N/A"}</Text>
            </View>
          </View>
          <View style={styles.divider} />
          <View style={styles.infoRow}>
            <Ionicons name="mail-outline" size={20} color="#757575" />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Email</Text>
              <Text style={styles.infoValue}>{user?.email || "N/A"}</Text>
            </View>
          </View>
          <View style={styles.divider} />
          <View style={styles.infoRow}>
            <Ionicons name="location-outline" size={20} color="#757575" />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>Region</Text>
              <Text style={styles.infoValue}>{user?.region || "N/A"}</Text>
            </View>
          </View>
        </Card>
        <PrimaryButton title="Logout" onPress={handleLogout} variant="danger" size="lg" style={styles.logoutButton} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8F9FA" },
  content: { flex: 1, padding: 20 },
  avatarSection: { alignItems: "center", marginBottom: 28 },
  avatar: { width: 88, height: 88, borderRadius: 44, backgroundColor: "#2E7D32", alignItems: "center", justifyContent: "center", marginBottom: 16 },
  avatarText: { fontSize: 36, fontWeight: "800", color: "#FFFFFF" },
  name: { fontSize: 22, fontWeight: "700", color: "#212121", marginBottom: 4 },
  email: { fontSize: 14, color: "#757575" },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 14 },
  infoContent: { flex: 1 },
  infoLabel: { fontSize: 12, color: "#757575", fontWeight: "500" },
  infoValue: { fontSize: 16, fontWeight: "600", color: "#212121", marginTop: 2 },
  divider: { height: 1, backgroundColor: "#F0F0F0" },
  logoutButton: { width: "100%", marginTop: 20 },
});
