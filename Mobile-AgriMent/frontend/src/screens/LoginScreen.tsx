import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import { PrimaryButton } from "../components";
import { Region } from "../types";

type Mode = "login" | "register";

export default function LoginScreen() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [region, setRegion] = useState<Region>("Occitanie");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async () => {
    if (mode === "register" && !name.trim()) {
      Alert.alert("Error", "Please enter your name");
      return;
    }
    if (!email.trim()) {
      Alert.alert("Error", "Please enter your email");
      return;
    }
    if (!password.trim() || password.length < 6) {
      Alert.alert("Error", "Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(name.trim(), email.trim(), password, region);
      }
    } catch (err: any) {
      const message =
        err.code === "ERR_NETWORK" || err.message === "Network Error"
          ? "Cannot reach server. Make sure the backend is running."
          : err.response?.data?.detail || "An error occurred";
      Alert.alert("Error", message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.logo}>🌾</Text>
          <Text style={styles.title}>AgriMent</Text>
          <Text style={styles.subtitle}>AI Pest Detection</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.tabRow}>
            <TouchableOpacity
              style={[styles.tab, mode === "login" && styles.activeTab]}
              onPress={() => setMode("login")}
            >
              <Text
                style={[
                  styles.tabText,
                  mode === "login" && styles.activeTabText,
                ]}
              >
                Login
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, mode === "register" && styles.activeTab]}
              onPress={() => setMode("register")}
            >
              <Text
                style={[
                  styles.tabText,
                  mode === "register" && styles.activeTabText,
                ]}
              >
                Sign Up
              </Text>
            </TouchableOpacity>
          </View>

          {mode === "register" && (
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Full Name</Text>
              <View style={styles.inputContainer}>
                <Ionicons name="person-outline" size={20} color="#757575" />
                <TextInput
                  style={styles.input}
                  placeholder="John Doe"
                  value={name}
                  onChangeText={setName}
                />
              </View>
            </View>
          )}

          <View style={styles.inputGroup}>
              <Text style={styles.label}>Email</Text>

            <View style={styles.inputContainer}>
              <Ionicons name="mail-outline" size={20} color="#757575" />
              <TextInput
                style={styles.input}
                placeholder="agriculteur@email.com"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
              <Text style={styles.label}>Password</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color="#757575" />
              <TextInput
                style={styles.input}
                placeholder="Min. 6 characters"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
              />
              <TouchableOpacity
                onPress={() => setShowPassword(!showPassword)}
              >
                <Ionicons
                  name={showPassword ? "eye-off-outline" : "eye-outline"}
                  size={20}
                  color="#757575"
                />
              </TouchableOpacity>
            </View>
          </View>

          {mode === "register" && (
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Region</Text>

              <View style={styles.inputContainer}>
                <Ionicons name="location-outline" size={20} color="#757575" />
                <TextInput
                  style={styles.input}
                  placeholder="Enter your region"
                  value={region}
                  onChangeText={setRegion as (t: string) => void}
                />
              </View>
            </View>
          )}

          <PrimaryButton
            title={mode === "login" ? "Log In" : "Create Account"}
            onPress={handleSubmit}
            loading={loading}
            size="lg"
            style={styles.submitButton}
          />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#2E7D32",
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 24,
  },
  header: {
    alignItems: "center",
    marginBottom: 40,
  },
  logo: {
    fontSize: 60,
    marginBottom: 12,
  },
  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "#FFFFFF",
  },
  subtitle: {
    fontSize: 14,
    color: "rgba(255,255,255,0.8)",
    marginTop: 4,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 28,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 8,
  },
  tabRow: {
    flexDirection: "row",
    backgroundColor: "#F5F5F5",
    borderRadius: 12,
    padding: 4,
    marginBottom: 24,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
    borderRadius: 10,
  },
  activeTab: {
    backgroundColor: "#2E7D32",
  },
  tabText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#757575",
  },
  activeTabText: {
    color: "#FFFFFF",
  },
  inputGroup: {
    marginBottom: 18,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#424242",
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#F8F9FA",
    borderRadius: 12,
    paddingHorizontal: 14,
    gap: 10,
  },
  input: {
    flex: 1,
    paddingVertical: 14,
    fontSize: 15,
    color: "#212121",
  },
  submitButton: {
    marginTop: 8,
    width: "100%",
  },
});
