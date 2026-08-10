import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface BulkActionBarProps {
  selectedCount: number;
  allSelected: boolean;
  totalItems: number;
  onSelectAll: () => void;
  onDelete: () => void;
  onCancel: () => void;
  deleting?: boolean;
}

export function BulkActionBar({
  selectedCount,
  allSelected,
  totalItems,
  onSelectAll,
  onDelete,
  onCancel,
  deleting,
}: BulkActionBarProps) {
  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.cancelButton} onPress={onCancel}>
        <Ionicons name="close" size={20} color="#757575" />
      </TouchableOpacity>

      <Text style={styles.countText}>
        {selectedCount} selected
      </Text>

      <TouchableOpacity
        style={styles.selectButton}
        onPress={onSelectAll}
      >
        <Ionicons
          name={allSelected ? "checkbox" : "square-outline"}
          size={20}
          color={allSelected ? "#2E7D32" : "#757575"}
        />
        <Text style={styles.selectButtonText}>
          {allSelected ? "Deselect All" : "Select All"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.deleteButton, (selectedCount === 0 || deleting) && styles.deleteButtonDisabled]}
        onPress={onDelete}
        disabled={selectedCount === 0 || deleting}
      >
        {deleting ? (
          <ActivityIndicator size="small" color="#FFF" />
        ) : (
          <Ionicons name="trash" size={18} color="#FFF" />
        )}
        <Text style={styles.deleteButtonText}>
          Delete{selectedCount > 0 ? ` (${selectedCount})` : ""}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#E0E0E0",
    gap: 8,
  },
  cancelButton: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "#F5F5F5",
    alignItems: "center",
    justifyContent: "center",
  },
  countText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#212121",
    flex: 1,
  },
  selectButton: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: "#F5F5F5",
    gap: 6,
  },
  selectButtonText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#757575",
  },
  deleteButton: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: "#D32F2F",
    gap: 6,
  },
  deleteButtonDisabled: {
    backgroundColor: "#E0E0E0",
  },
  deleteButtonText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FFFFFF",
  },
});
