import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  Alert,
  ScrollView,
  Platform,
  TextInput,
  Keyboard,
  KeyboardAvoidingView,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { Ionicons } from "@expo/vector-icons";
import { Header, PrimaryButton, LoadingSpinner } from "../components";
import { useDetection } from "../hooks/useDetection";
import { useAuth } from "../context/AuthContext";
import { regionService } from "../services/region";
import { REGIONS_FALLBACK } from "../types";

const isWebPlatform = Platform.OS === "web" || (typeof window !== "undefined" && typeof document !== "undefined");

export default function DetectScreen({ navigation }: any) {
  const { user } = useAuth();
  const { isAnalyzing, analyze, reset } = useDetection();
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [region, setRegion] = useState(user?.region || "Occitanie");
  const [regionSearchQuery, setRegionSearchQuery] = useState(user?.region || "");
  const [showRegionSuggestions, setShowRegionSuggestions] = useState(false);
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [availableRegions, setAvailableRegions] = useState<string[]>(REGIONS_FALLBACK);

  // Fetch available regions on component mount
  useEffect(() => {
    (async () => {
      try {
        const regions = await regionService.getAvailableRegions();
        // Only update if we got results from the backend
        if (regions && regions.length > 0) {
          setAvailableRegions(regions);
          // If user's region is not in the available regions, set to first available
          if (!regions.includes(region)) {
            setRegion(regions[0]);
            setRegionSearchQuery(regions[0]);
          }
        }
      } catch (error) {
        console.warn("Failed to fetch regions, using fallback:", error);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === "granted") {
          const loc = await Location.getCurrentPositionAsync({});
          setLocation({ latitude: loc.coords.latitude, longitude: loc.coords.longitude });
        }
      } catch {}
    })();
  }, []);

  const clearSelectedImage = () => {
    if (imageUri?.startsWith("blob:")) {
      URL.revokeObjectURL(imageUri);
    }
    setImageUri(null);
    setImageFile(null);
  };

  const pickImage = async (useCamera: boolean) => {
    if (isWebPlatform) {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      if (useCamera) {
        input.capture = "environment";
      }
      input.style.display = "none";

      input.onchange = (event) => {
        const file = (event.target as HTMLInputElement).files?.[0];
        if (file) {
          if (imageUri?.startsWith("blob:")) {
            URL.revokeObjectURL(imageUri);
          }
          const objectUrl = URL.createObjectURL(file);
          setImageUri(objectUrl);
          setImageFile(file);
        }
        document.body.removeChild(input);
      };

      document.body.appendChild(input);
      input.click();
      return;
    }

    try {
      let result;
      if (useCamera) {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          Alert.alert(
            "Permission Required",
            "Camera access is needed to take photos of insects."
          );
          return;
        }
        result = await ImagePicker.launchCameraAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          allowsEditing: true,
        });
      } else {
        const permission =
          await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
          Alert.alert(
            "Permission Required",
            "Gallery access is needed to select images."
          );
          return;
        }
        result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          allowsEditing: true,
        });
      }

      if (!result.canceled && result.assets[0]) {
        setImageUri(result.assets[0].uri);
        setImageFile(null);
      }
    } catch (error) {
      Alert.alert("Error", "Failed to pick image. Please try again.");
    }
  };

  const handleAnalyze = async () => {
    const selectedImage = imageFile ?? imageUri;
    if (!selectedImage) {
      Alert.alert("Error", "Please select or take an image first");
      return;
    }

    try {
      const result = await analyze(
        selectedImage,
        region,
        location?.latitude,
        location?.longitude
      );
      navigation.navigate("Result", { detection: result });
    } catch (error: any) {
      Alert.alert("Analysis Failed", error.message || "Please try again");
    }
  };

  // Filter regions by search query for autocomplete
  const filteredRegions = availableRegions.filter((r) =>
    r.toLowerCase().includes(regionSearchQuery.toLowerCase())
  );

  const selectRegion = (r: string) => {
    setRegion(r);
    setRegionSearchQuery(r);
    setShowRegionSuggestions(false);
    Keyboard.dismiss();
  };

  if (isAnalyzing) {
    return (
      <View style={styles.container}>
        <Header
          title="Analyzing..."
          showBack
          onBack={() => {
            reset();
            clearSelectedImage();
          }}
        />
        <LoadingSpinner />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <Header title="Detect an Insect" showBack onBack={() => navigation.goBack()} />

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
      >
        {!imageUri ? (
          <View style={styles.placeholderContainer}>
            <View style={styles.placeholder}>
              <Ionicons name="camera-outline" size={80} color="#BDBDBD" />
              <Text style={styles.placeholderText}>
                Take a photo or select from gallery
              </Text>
            </View>
          </View>
        ) : (
          <View style={styles.previewContainer}>
            <Image source={{ uri: imageUri }} style={styles.preview} />
            <TouchableOpacity
              style={styles.removeButton}
              onPress={clearSelectedImage}
            >
              <Ionicons name="close-circle" size={32} color="#D32F2F" />
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={styles.actionCard}
            onPress={() => pickImage(true)}
          >
            <Ionicons name="camera" size={32} color="#2E7D32" />
            <Text style={styles.actionTitle}>Camera</Text>
            <Text style={styles.actionSubtitle}>Take a photo</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionCard}
            onPress={() => pickImage(false)}
          >
            <Ionicons name="images" size={32} color="#4CAF50" />
            <Text style={styles.actionTitle}>Gallery</Text>
            <Text style={styles.actionSubtitle}>Choose from album</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.regionSection}>
          <Text style={styles.regionLabel}>Detection Region</Text>
          <View style={styles.regionSelector}>
            <Ionicons name="location-outline" size={20} color="#757575" />
            <TextInput
              style={styles.regionInput}
              value={regionSearchQuery}
              onChangeText={(text) => {
                setRegionSearchQuery(text);
                setShowRegionSuggestions(true);
                // If text doesn't match a known region, clear the selected region
                const match = availableRegions.find(
                  (r) => r.toLowerCase() === text.toLowerCase()
                );
                if (match) {
                  setRegion(match);
                }
              }}
              onFocus={() => setShowRegionSuggestions(true)}
              placeholder="Type to search a region..."
              placeholderTextColor="#BDBDBD"
            />
            {regionSearchQuery.length > 0 && (
              <TouchableOpacity onPress={() => {
                setRegionSearchQuery("");
                setShowRegionSuggestions(false);
              }}>
                <Ionicons name="close-circle" size={18} color="#BDBDBD" />
              </TouchableOpacity>
            )}
          </View>

          {showRegionSuggestions && (
            <View style={styles.suggestions}>
              {filteredRegions.length === 0 && regionSearchQuery.length > 0 && (
                <View style={styles.suggestionItem}>
                  <Ionicons name="search-outline" size={16} color="#BDBDBD" />
                  <Text style={[styles.suggestionText, { color: "#BDBDBD" }]}>
                    No regions found for "{regionSearchQuery}"
                  </Text>
                </View>
              )}
              {filteredRegions.map((r) => (
                <TouchableOpacity
                  key={r}
                  style={[
                    styles.suggestionItem,
                    region === r && styles.suggestionItemActive,
                  ]}
                  onPress={() => selectRegion(r)}
                >
                  <Ionicons
                    name={region === r ? "radio-button-on" : "radio-button-off"}
                    size={16}
                    color={region === r ? "#2E7D32" : "#BDBDBD"}
                  />
                  <Text
                    style={[
                      styles.suggestionText,
                      region === r && styles.suggestionTextActive,
                    ]}
                  >
                    {r}
                  </Text>
                  {region === r && <Ionicons name="checkmark" size={16} color="#2E7D32" />}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {location && (
          <View style={styles.locationBadge}>
            <Ionicons name="navigate" size={14} color="#4CAF50" />
            <Text style={styles.locationText}>
              GPS: {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
            </Text>
          </View>
        )}

        <PrimaryButton
            title="Analyze Insect"
          onPress={handleAnalyze}
          disabled={!imageUri}
          size="lg"
          style={styles.analyzeButton}
        />
      </ScrollView>
    </KeyboardAvoidingView>
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
  placeholderContainer: {
    marginBottom: 24,
  },
  placeholder: {
    height: 260,
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: "#E0E0E0",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholderText: {
    fontSize: 16,
    color: "#BDBDBD",
    marginTop: 12,
  },
  previewContainer: {
    position: "relative",
    marginBottom: 24,
  },
  preview: {
    width: "100%",
    height: 280,
    borderRadius: 24,
  },
  removeButton: {
    position: "absolute",
    top: 12,
    right: 12,
  },
  actionButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
  },
  actionCard: {
    width: "48%",
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 24,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#212121",
    marginTop: 10,
  },
  actionSubtitle: {
    fontSize: 12,
    color: "#757575",
    marginTop: 4,
  },
  regionSection: {
    marginBottom: 16,
    zIndex: 20,
  },
  regionLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#424242",
    marginBottom: 12,
  },
  regionSelector: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    paddingHorizontal: 14,
    borderWidth: 2,
    borderColor: "#E0E0E0",
    gap: 10,
  },
  regionInput: {
    flex: 1,
    paddingVertical: 14,
    fontSize: 15,
    color: "#212121",
  },
  suggestions: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    marginTop: 4,
    borderWidth: 1,
    borderColor: "#E0E0E0",
    maxHeight: 200,
    overflow: "hidden",
  },
  suggestionItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: "#F0F0F0",
  },
  suggestionItemActive: {
    backgroundColor: "#E8F5E9",
  },
  suggestionText: {
    flex: 1,
    fontSize: 14,
    color: "#424242",
  },
  suggestionTextActive: {
    color: "#2E7D32",
    fontWeight: "700",
  },
  locationBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#E8F5E9",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 16,
    alignSelf: "flex-start",
    gap: 6,
  },
  locationText: {
    fontSize: 12,
    color: "#2E7D32",
    fontWeight: "500",
  },
  analyzeButton: {
    width: "100%",
  },
});
