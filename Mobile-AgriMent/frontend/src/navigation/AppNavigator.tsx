import React, { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import * as Linking from "expo-linking";
import { AuthProvider, useAuth } from "../context/AuthContext";
import {
  SplashScreen,
  LoginScreen,
  HomeScreen,
  DetectScreen,
  ResultScreen,
  NotificationsScreen,
  NotificationDetailScreen,
  HistoryScreen,
  ProfileScreen,
  MapScreen,
} from "../screens";
import { PrimaryButton } from "../components";
import {
  registerForPushNotifications,
  cleanupNotificationListeners,
  navigationRef,
} from "../utils/notifications";
import { useConnectivity } from "../hooks/useConnectivity";
import { API_BASE_URL } from "../utils/config";
import { farmerManager } from "../utils/farmerManager";

const Stack = createNativeStackNavigator();

function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
    </Stack.Navigator>
  );
}

function AppStack() {
  useEffect(() => {
    // Fire-and-forget: push registration must never block or crash the app.
    void registerForPushNotifications().catch((error) => {
      console.warn("Push registration promise rejected (ignored):", error);
    });

    const handleDeepLink = async (url: string | null) => {
      if (!url) return;
      try {
        const parsed = Linking.parse(url);
        const farmerId = parsed.queryParams?.farmer_id || parsed.queryParams?.farmerId;
        if (typeof farmerId === "string" && farmerId.trim()) {
          await farmerManager.saveFarmerId(farmerId.trim());
        }
      } catch (error) {
        console.warn("Failed to parse deep link URL:", error);
      }
    };

    void Linking.getInitialURL().then(handleDeepLink);

    const subscription = Linking.addEventListener("url", (event) => {
      handleDeepLink(event.url);
    });

    return () => {
      subscription.remove();
      cleanupNotificationListeners();
    };
  }, []);

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="HomeTab" component={HomeScreen} />
      <Stack.Screen name="Detect" component={DetectScreen} />
      <Stack.Screen name="Result" component={ResultScreen} />
      <Stack.Screen name="Notifications" component={NotificationsScreen} />
      <Stack.Screen name="NotificationDetail" component={NotificationDetailScreen} />
      <Stack.Screen name="Map" component={MapScreen} />
      <Stack.Screen name="History" component={HistoryScreen} />
      <Stack.Screen name="Profile" component={ProfileScreen} />
    </Stack.Navigator>
  );
}

function OfflineScreen({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={offlineStyles.container}>
      <Ionicons name="cloud-offline-outline" size={64} color="#BDBDBD" />
      <Text style={offlineStyles.title}>No connection to server</Text>
      <Text style={offlineStyles.message}>
        Cannot reach the backend at:
        {"\n"}
        {API_BASE_URL}
      </Text>
      <Text style={offlineStyles.hint}>
        Make sure you are on the same WiFi network as the PC running the backend.
      </Text>
      <PrimaryButton title="Retry" onPress={onRetry} size="md" />
    </View>
  );
}

function RootNavigator() {
  const { isAuthenticated, isLoading } = useAuth();
  const connectivity = useConnectivity();

  if (connectivity.isChecking) {
    return <SplashScreen />;
  }

  if (!connectivity.isConnected) {
    return <OfflineScreen onRetry={connectivity.retry} />;
  }

  return (
    <NavigationContainer ref={navigationRef}>
      {isAuthenticated ? <AppStack /> : <AuthStack />}
    </NavigationContainer>
  );
}

export default function AppNavigator() {
  return (
    <AuthProvider>
      <RootNavigator />
    </AuthProvider>
  );
}

const offlineStyles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    backgroundColor: "#F8F9FA",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#212121",
    marginTop: 16,
    marginBottom: 12,
    textAlign: "center",
  },
  message: {
    fontSize: 15,
    color: "#616161",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 8,
  },
  hint: {
    fontSize: 13,
    color: "#9E9E9E",
    textAlign: "center",
    lineHeight: 18,
    marginBottom: 24,
  },
});

