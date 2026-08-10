import React, { useState, useCallback } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { Header, DetectionCard, BulkActionBar } from "../components";
import { useBulkSelection } from "../hooks/useBulkSelection";
import { detectionService } from "../services/detection";
import { Detection } from "../types";

export default function HistoryScreen({ navigation }: any) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    try {
      const data = await detectionService.getHistory();
      setDetections(data.detections);
    } catch (error) {
      console.warn("Failed to load history:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { loadHistory(); }, []));

  const bulk = useBulkSelection<Detection>({
    items: detections,
    getItemId: (d) => d.id,
    itemName: "detections",
    onDelete: async (ids) => {
      await detectionService.bulkDelete(ids);
      setDetections((prev) => prev.filter((d) => !ids.includes(d.id)));
    },
  });

  const handleItemPress = (item: Detection) => {
    if (bulk.selectionMode) {
      bulk.toggleSelection(item.id);
    } else {
      navigation.navigate("Result", { detection: item });
    }
  };

  return (
    <View style={styles.container}>
      <Header
        title="History"
        subtitle={bulk.selectionMode ? `${bulk.selectedCount} of ${detections.length} selected` : `${detections.length} detections`}
        showBack
        onBack={() => bulk.selectionMode ? bulk.exitSelectionMode() : navigation.goBack()}
        rightAction={
          detections.length > 0 && !bulk.selectionMode
            ? { icon: "trash-outline", onPress: bulk.enterSelectionMode }
            : undefined
        }
      />

      {bulk.selectionMode && (
        <BulkActionBar
          selectedCount={bulk.selectedCount}
          allSelected={bulk.allSelected}
          totalItems={detections.length}
          onSelectAll={bulk.toggleAll}
          onDelete={bulk.confirmDelete}
          onCancel={bulk.exitSelectionMode}
          deleting={bulk.deleting}
        />
      )}

      {loading ? (
        <View style={styles.centered}><Text style={styles.loadingText}>Loading...</Text></View>
      ) : detections.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyTitle}>No Detections</Text>
          <Text style={styles.emptyText}>Your history will appear after your first scan.</Text>
        </View>
      ) : (
        <FlatList
          data={detections}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => {
            const isSelected = bulk.selectedIds.has(item.id);
            return (
              <TouchableOpacity
                style={[styles.listItem, isSelected && styles.listItemSelected]}
                onPress={() => handleItemPress(item)}
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
                  <DetectionCard detection={item} onPress={() => handleItemPress(item)} />
                </View>
              </TouchableOpacity>
            );
          }}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadHistory(); }} />}
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
    borderRadius: 20,
  },
  checkbox: {
    marginRight: 8,
    marginLeft: 4,
  },
  cardWrapper: {
    flex: 1,
  },
});
