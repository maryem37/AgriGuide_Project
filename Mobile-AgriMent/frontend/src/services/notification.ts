import api from "./api";
import { NotificationListResponse } from "../types";
import { farmerManager } from "../utils/farmerManager";

export const notificationService = {
  async getNotifications(
    skip: number = 0,
    limit: number = 50
  ): Promise<NotificationListResponse> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.get<NotificationListResponse>(
      "/notifications",
      { params: { skip, limit, farmer_id: farmerId } }
    );
    return data;
  },

  async markAsRead(notificationIds: string[]): Promise<void> {
    const farmerId = await farmerManager.getFarmerId();
    await api.post("/notifications/read", {
      notification_ids: notificationIds,
      farmer_id: farmerId,
    });
  },

  async bulkDelete(ids: string[]): Promise<{ deleted: number; ids: string[] }> {
    const farmerId = await farmerManager.getFarmerId();
    const { data } = await api.post("/notifications/bulk-delete", {
      ids,
      farmer_id: farmerId,
    });
    return data;
  },
};
