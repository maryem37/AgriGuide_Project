import { Platform } from "react-native";
import api from "./api";
import { Detection, DetectionHistoryResponse } from "../types";
import { farmerManager } from "../utils/farmerManager";

type ImageInput = string | File;
const isWebPlatform = Platform.OS === "web" || (typeof window !== "undefined" && typeof document !== "undefined");

async function buildFormData(image: ImageInput, region: string, latitude?: number | null, longitude?: number | null) {
  const formData = new FormData();

  const farmerId = await farmerManager.getFarmerId();
  if (farmerId) {
    formData.append("farmer_id", farmerId);
  }

  const isFile = typeof File !== "undefined" && image instanceof File;
  if (isFile) {
    formData.append("image", image, image.name);
  } else {
    const imageUri = image as string;
    const filename = imageUri.split("/").pop()?.split("?")[0] || "image.jpg";
    const match = /\.(\w+)$/.exec(filename);
    const ext = match?.[1]?.toLowerCase() || "jpg";
    const type =
      ext === "jpg" || ext === "jpeg"
        ? "image/jpeg"
        : ext === "png"
          ? "image/png"
          : ext === "webp"
            ? "image/webp"
            : "image/jpeg";

    if (isWebPlatform) {
      const response = await fetch(imageUri);
      const blob = await response.blob();
      formData.append("image", blob, filename);
    } else {
      formData.append("image", {
        uri: imageUri,
        name: filename,
        type,
      } as any);
    }
  }

  formData.append("region", region);
  if (latitude != null) formData.append("latitude", String(latitude));
  if (longitude != null) formData.append("longitude", String(longitude));
  return formData;
}

export const detectionService = {
  async detectInsect(image: ImageInput, region: string, latitude?: number | null, longitude?: number | null): Promise<Detection> {
    const formData = await buildFormData(image, region, latitude, longitude);

    const { data } = await api.post<Detection>("/detect", formData, {
      timeout: 120000,
      headers: {
        "Content-Type": undefined,
      },
    });
    return data;
  },

  async getHistory(skip = 0, limit = 20): Promise<DetectionHistoryResponse> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.get<DetectionHistoryResponse>("/detect/history", {
      params: { skip, limit, farmer_id: farmerId },
    });
    return data;
  },

  async getDetection(id: string): Promise<Detection> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.get<Detection>(`/detect/${id}`, {
      params: { farmer_id: farmerId },
    });
    return data;
  },

  async sendAlert(detectionId: string): Promise<Detection> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.post<Detection>(`/detect/${detectionId}/alert-region`, {
      farmer_id: farmerId,
    });
    return data;
  },

  async getRegionDetections(regionName: string): Promise<{ detections: Detection[]; total: number }> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.get(`/detect/region/${encodeURIComponent(regionName)}`, {
      params: { farmer_id: farmerId },
    });
    return data;
  },

  async getAllDetections(): Promise<{ detections: Detection[]; total: number }> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.get("/detect/all", {
      params: { farmer_id: farmerId },
    });
    return data;
  },

  async bulkDelete(ids: string[]): Promise<{ deleted: number; ids: string[] }> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.post("/detect/bulk-delete", { ids, farmer_id: farmerId });
    return data;
  },
};
