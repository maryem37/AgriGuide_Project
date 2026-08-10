import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Notification } from "../types";

interface NotificationCardProps {
  notification: Notification;
  onPress?: () => void;
}

export function NotificationCard({
  notification,
  onPress,
}: NotificationCardProps) {
  const timeAgo = getTimeAgo(notification.created_at);

  return (
    <TouchableOpacity
      style={[
        styles.container,
        !notification.is_read && styles.unread,
      ]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <View style={styles.iconContainer}>
        <Ionicons
          name={notification.is_read ? "notifications-outline" : "notifications"}
          size={24}
          color={notification.is_read ? "#757575" : "#FF9800"}
        />
      </View>

      <View style={styles.content}>
        <View style={styles.header}>
          <Text
            style={[styles.title, !notification.is_read && styles.unreadTitle]}
            numberOfLines={1}
          >
            {notification.title}
          </Text>
          <Text style={styles.time}>{timeAgo}</Text>
        </View>

        <Text style={styles.species} numberOfLines={1}>
          {notification.species}
        </Text>

        <Text style={styles.message} numberOfLines={2}>
          {notification.message}
        </Text>

        <View style={styles.footer}>
          <View style={styles.regionBadge}>
            <Ionicons name="location" size={12} color="#2E7D32" />
            <Text style={styles.regionText}>{notification.region}</Text>
          </View>
        </View>
      </View>

      {!notification.is_read && <View style={styles.unreadDot} />}
    </TouchableOpacity>
  );
}

function getTimeAgo(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "now";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  return `${diffDays}d`;
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  unread: {
    backgroundColor: "#FFF8E1",
    borderLeftWidth: 4,
    borderLeftColor: "#FF9800",
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: "#FFF3E0",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  content: { flex: 1 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  title: {
    fontSize: 14,
    fontWeight: "600",
    color: "#757575",
    flex: 1,
    marginRight: 8,
  },
  unreadTitle: {
    fontWeight: "700",
    color: "#212121",
  },
  time: {
    fontSize: 12,
    color: "#BDBDBD",
  },
  species: {
    fontSize: 15,
    fontWeight: "700",
    color: "#2E7D32",
    marginBottom: 4,
  },
  message: {
    fontSize: 13,
    color: "#757575",
    lineHeight: 18,
    marginBottom: 8,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
  },
  regionBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#E8F5E9",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  regionText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#2E7D32",
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#FF9800",
    marginLeft: 8,
    alignSelf: "center",
  },
});
