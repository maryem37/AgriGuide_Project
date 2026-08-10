import AsyncStorage from "@react-native-async-storage/async-storage";

const FARMER_ID_KEY = "farmer_id";

// Check environment variables for anonymous mode flag
const IS_ANONYMOUS_MODE =
  process.env.EXPO_PUBLIC_ANONYMOUS === "true" ||
  process.env.REACT_APP_ANONYMOUS === "true" ||
  process.env.ANONYMOUS === "true";

export const farmerManager = {
  /**
   * Save farmer ID to device storage when user logs in or scans QR code.
   */
  async saveFarmerId(farmerId: string): Promise<void> {
    if (!farmerId) return;
    try {
      await AsyncStorage.setItem(FARMER_ID_KEY, farmerId);
      console.log(`[FarmerManager] Saved farmer_id: ${farmerId}`);
    } catch (error) {
      console.error("[FarmerManager] Error saving farmer_id:", error);
    }
  },

  /**
   * Get current farmer ID.
   * In anonymous mode, returns 'anonymous_guest'.
   * In login mode, returns stored farmer_id or fallback 'anonymous_guest' if not logged in.
   */
  async getFarmerId(): Promise<string> {
    if (IS_ANONYMOUS_MODE) {
      return "anonymous_guest";
    }
    try {
      const storedId = await AsyncStorage.getItem(FARMER_ID_KEY);
      return storedId || "anonymous_guest";
    } catch (error) {
      console.error("[FarmerManager] Error reading farmer_id:", error);
      return "anonymous_guest";
    }
  },

  /**
   * Remove stored farmer ID (logout).
   */
  async clearFarmerId(): Promise<void> {
    try {
      await AsyncStorage.removeItem(FARMER_ID_KEY);
      console.log("[FarmerManager] Cleared farmer_id");
    } catch (error) {
      console.error("[FarmerManager] Error clearing farmer_id:", error);
    }
  },

  /**
   * Check if application is explicitly running in anonymous mode.
   */
  isAnonymousMode(): boolean {
    return IS_ANONYMOUS_MODE;
  },
};

export default farmerManager;
