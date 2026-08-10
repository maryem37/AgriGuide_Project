import * as Notifications from "expo-notifications";
import { Audio } from "expo-av";
import Constants, { ExecutionEnvironment } from "expo-constants";
import * as Device from "expo-device";
import { createNavigationContainerRef } from "@react-navigation/native";
import { Platform } from "react-native";
import { authService } from "../services/auth";
import { Notification, Region, RootStackParamList } from "../types";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

let isListenerSetup = false;
let notificationListenerSubscription: Notifications.EventSubscription | null = null;
let responseListenerSubscription: Notifications.EventSubscription | null = null;

function isExpoGo(): boolean {
  return Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
}

function getExpoProjectId(): string | null {
  const config = Constants.expoConfig;
  const projectId =
    config?.extra?.eas?.projectId ??
    (config as { projectId?: string } | null)?.projectId ??
    Constants.easConfig?.projectId ??
    (Constants.manifest as { extra?: { eas?: { projectId?: string } } } | null)
      ?.extra?.eas?.projectId ??
    null;

  return typeof projectId === "string" && projectId.length > 0 ? projectId : null;
}

async function registerDeviceTokenWithBackend(deviceToken: string): Promise<void> {
  try {
    const storedToken = await authService.getStoredToken();
    if (!storedToken) {
      console.warn("[Push] No auth token stored — cannot register device token with backend");
      return;
    }

    await authService.updateDeviceToken(deviceToken);
    console.log("[Push] Device token registered with backend:", deviceToken.substring(0, 30) + "...");
  } catch (error) {
    console.warn("[Push] Could not register device token with backend:", error);
  }
}

export async function registerForPushNotifications(): Promise<string | null> {
  if (Platform.OS === "web") {
    console.warn("[Push] Push notifications are not supported on web");
    return null;
  }

  setupNotificationListeners();

  if (!Device.isDevice) {
    console.warn("[Push] Skipped: not a physical device");
    return null;
  }

  if (Platform.OS === "android" && isExpoGo()) {
    console.warn("[Push] Skipped on Android Expo Go (SDK 53+ does not support remote push)");
    return null;
  }

  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    console.log("[Push] Current permission status:", existingStatus);

    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync({
        ios: {
          allowAlert: true,
          allowBadge: true,
          allowSound: true,
        },
      });
      finalStatus = status;
      console.log("[Push] Permission after request:", finalStatus);
    }

    if (finalStatus !== "granted") {
      console.warn("[Push] Permission not granted — push notifications disabled");
      return null;
    }

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("pest_alerts", {
        name: "Pest Alerts",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 500, 250, 500],
        lightColor: "#D32F2F",
        sound: "default",
      });
      console.log("[Push] Android notification channel 'pest_alerts' created (MAX importance)");
    }

    const projectId = getExpoProjectId();
    if (!projectId) {
      console.warn("[Push] No Expo projectId found — cannot obtain push token");
      console.warn("[Push] Add extra.eas.projectId to app.json");
      return null;
    }
    console.log("[Push] Using Expo project ID:", projectId);

    let deviceToken: string | null = null;
    try {
      const tokenResponse = await Notifications.getExpoPushTokenAsync({ projectId });
      deviceToken = tokenResponse.data;
      console.log("[Push] Expo push token obtained:", deviceToken);
    } catch (error) {
      console.warn("[Push] Could not obtain Expo push token:", error);
      return null;
    }

    if (deviceToken) {
      await registerDeviceTokenWithBackend(deviceToken);
    }

    return deviceToken;
  } catch (error) {
    console.warn("[Push] Registration failed:", error);
    return null;
  }
}

export function setupNotificationListeners() {
  if (isListenerSetup) return;
  isListenerSetup = true;

  notificationListenerSubscription = Notifications.addNotificationReceivedListener(
    (notification) => {
      console.log("[Push] Foreground notification received:", {
        title: notification.request.content.title,
        body: notification.request.content.body,
        data: notification.request.content.data,
      });
    }
  );

  responseListenerSubscription = Notifications.addNotificationResponseReceivedListener(
    (response) => {
      console.log("[Push] Notification tapped:", response.notification.request.content.title);
      handleNotificationNavigation(response.notification);
    }
  );

  void checkInitialNotification();
}

async function checkInitialNotification() {
  try {
    const lastResponse = await Notifications.getLastNotificationResponseAsync();
    if (lastResponse) {
      console.log("[Push] Initial notification response found, navigating...");
      setTimeout(() => {
        handleNotificationNavigation(lastResponse.notification);
      }, 600);
    }
  } catch (error) {
    console.warn("[Push] Could not read initial notification response:", error);
  }
}

function handleNotificationNavigation(notification: Notifications.Notification) {
  const content = notification.request.content;
  const data = content.data || {};
  const detectionId = (data.detection_id || data.detectionId) as string | undefined;

  const notificationParam: Notification = {
    id: notification.request.identifier || String(Date.now()),
    detection_id: detectionId,
    title: content.title || "Pest Alert",
    message: content.body || "",
    species: (data.species as string) || "Unknown Species",
    region: ((data.region as string) || "All Regions") as Region,
    is_read: true,
    created_at: new Date().toISOString(),
  };

  const navigate = () => {
    if (detectionId) {
      navigationRef.navigate("NotificationDetail", {
        notification: notificationParam,
      });
    } else {
      navigationRef.navigate("Notifications");
    }
  };

  if (navigationRef.isReady()) {
    navigate();
  } else {
    setTimeout(() => {
      if (navigationRef.isReady()) {
        navigate();
      }
    }, 500);
  }
}

export async function showDemoAlertNotification({
  detectionId,
  species,
  region,
}: {
  detectionId?: string;
  species: string;
  region: string;
}): Promise<boolean> {
  if (Platform.OS === "web") {
    console.warn("[Push] Local demo notifications not supported on web");
    return false;
  }

  try {
    const { status } = await Notifications.getPermissionsAsync();
    let finalStatus = status;

    if (status !== "granted") {
      const requested = await Notifications.requestPermissionsAsync({
        ios: {
          allowAlert: true,
          allowBadge: true,
          allowSound: true,
        },
      });
      finalStatus = requested.status;
    }

    if (finalStatus !== "granted") {
      console.warn("[Push] Demo notification permission not granted");
      return false;
    }

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("pest_alerts", {
        name: "Pest Alerts",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 500, 250, 500],
        lightColor: "#D32F2F",
        sound: "default",
        showBadge: true,
      });
    }

    await Notifications.scheduleNotificationAsync({
      content: {
        title: `🚨 URGENT: ${species} detected`,
        body: `Immediate action needed in ${region}. Open the app now to review the alert.`,
        sound: "default",
        priority: Notifications.AndroidNotificationPriority.MAX,
        ...(Platform.OS === "android" ? { channelId: "pest_alerts" } : {}),
        data: {
          detection_id: detectionId,
          species,
          region,
        },
      },
      trigger: null,
    });

    console.log("[Push] Local demo notification scheduled for:", species, "in", region);

    try {
      const { sound } = await Audio.Sound.createAsync(
        require("../../assets/alert-sound.wav")
      );
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        staysActiveInBackground: false,
      });
      await sound.playAsync();
      setTimeout(() => {
        void sound.unloadAsync();
      }, 2500);
    } catch (audioError) {
      console.warn("[Push] Could not play alert sound (non-critical):", audioError);
    }

    return true;
  } catch (error) {
    console.error("[Push] Could not show demo notification:", error);
    return false;
  }
}

export function cleanupNotificationListeners() {
  if (notificationListenerSubscription) {
    notificationListenerSubscription.remove();
    notificationListenerSubscription = null;
  }
  if (responseListenerSubscription) {
    responseListenerSubscription.remove();
    responseListenerSubscription = null;
  }
  isListenerSetup = false;
}
