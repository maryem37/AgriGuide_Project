import React, { useState, useCallback } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { Header, NotificationCard, BulkActionBar } from "../components";
import { useBulkSelection } from "../hooks/useBulkSelection";
import { notificationService } from "../services/notification";
import { Notification } from "../types";

export default function NotificationsScreen({ navigation }: any) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadNotifications = async () => {
    try {
      const data = await notificationService.getNotifications();
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (error) {
      console.warn("Failed to load notifications:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadNotifications(); }, []));

  const bulk = useBulkSelection<Notification>({
    items: notifications,
    getItemId: (n) => n.id,
    itemName: "alerts",
    onDelete: async (ids) => {
      await notificationService.bulkDelete(ids);
      setNotifications((prev) => prev.filter((n) => !ids.includes(n.id)));
      setUnreadCount((prev) => {
        const deletedUnread = notifications.filter((n) => ids.includes(n.id) && !n.is_read).length;
        return Math.max(0, prev - deletedUnread);
      });
    },
  });

  const handleNotificationPress = async (notification: Notification) => {
    if (bulk.selectionMode) {
      bulk.toggleSelection(notification.id);
      return;
    }
    if (!notification.is_read) {
      try {
        await notificationService.markAsRead([notification.id]);
        setNotifications((prev) => prev.map((n) => n.id === notification.id ? { ...n, is_read: true } : n));
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (error) {}
    }
    navigation.navigate("NotificationDetail", { notification });
  };

  return (
    <View style={styles.container}>
      <Header
        title="Notifications"
        subtitle={bulk.selectionMode ? `${bulk.selectedCount} of ${notifications.length} selected` : `${unreadCount} unread alerts`}
        showBack
        onBack={() => bulk.selectionMode ? bulk.exitSelectionMode() : navigation.goBack()}
        rightAction={
          notifications.length > 0 && !bulk.selectionMode
            ? { icon: "trash-outline", onPress: bulk.enterSelectionMode }
            : undefined
        }
      />

      {bulk.selectionMode && (
        <BulkActionBar
          selectedCount={bulk.selectedCount}
          allSelected={bulk.allSelected}
          totalItems={notifications.length}
          onSelectAll={bulk.toggleAll}
          onDelete={bulk.confirmDelete}
          onCancel={bulk.exitSelectionMode}
          deleting={bulk.deleting}
        />
      )}

      {loading ? (
        <View style={styles.centered}><Text style={styles.loadingText}>Loading...</Text></View>
      ) : notifications.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyIcon}>🔔</Text>
          <Text style={styles.emptyTitle}>No Notifications</Text>
          <Text style={styles.emptyText}>You will receive alerts when insects are detected in your region.</Text>
        </View>
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => {
            const isSelected = bulk.selectedIds.has(item.id);
            return (
              <TouchableOpacity
                style={[styles.listItem, isSelected && styles.listItemSelected]}
                onPress={() => handleNotificationPress(item)}
                activeOpacity={bulk.selectionMode ? 0.6 : 0.8}
              >
                {bulk.selectionMode && (
                  <View style={styles.checkbox}>
                    <Ionicons
                      name={isSelected ? "checkbox" : "square-outline"}
                      size={22}
                      color={isSelected ? "#2E7D32" : "#BDBDBD"}
                    />
                  </View>
                )}
                <View style={styles.cardWrapper}>
                  <NotificationCard notification={item} onPress={() => handleNotificationPress(item)} />
                </View>
              </TouchableOpacity>
            );
          }}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadNotifications(); }} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8F9FA" },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 40 },
  loadingText: { fontSize: 16, color: "#757575" },
  emptyIcon: { fontSize: 60, marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: "700", color: "#212121", marginBottom: 8 },
  emptyText: { fontSize: 14, color: "#757575", textAlign: "center", lineHeight: 20 },
  listContent: { padding: 16 },
  listItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  listItemSelected: {
    backgroundColor: "#E8F5E9",
    borderRadius: 16,
  },
  checkbox: {
    marginRight: 8,
    marginLeft: 4,
  },
  cardWrapper: {
    flex: 1,
  },
});
