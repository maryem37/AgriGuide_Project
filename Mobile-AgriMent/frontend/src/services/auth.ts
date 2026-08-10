import api from "./api";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  AuthResponse,
  Detection,
  DetectionHistoryResponse,
  NotificationListResponse,
  Region,
} from "../types";

export const authService = {
  async register(
    name: string,
    email: string,
    password: string,
    region: Region
  ): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/auth/register", {
      name,
      email,
      password,
      region,
    });
    await AsyncStorage.setItem("auth_token", data.access_token);
    await AsyncStorage.setItem("user_data", JSON.stringify(data.user));
    return data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/auth/login", {
      email,
      password,
    });
    await AsyncStorage.setItem("auth_token", data.access_token);
    await AsyncStorage.setItem("user_data", JSON.stringify(data.user));
    return data;
  },

  async logout(): Promise<void> {
    await AsyncStorage.removeItem("auth_token");
    await AsyncStorage.removeItem("user_data");
  },

  async getStoredUser() {
    const userData = await AsyncStorage.getItem("user_data");
    return userData ? JSON.parse(userData) : null;
  },

  async getStoredToken(): Promise<string | null> {
    return AsyncStorage.getItem("auth_token");
  },

  async updateDeviceToken(deviceToken: string): Promise<void> {
    await api.post("/auth/device-token", null, {
      params: { device_token: deviceToken },
    });
  },
};
