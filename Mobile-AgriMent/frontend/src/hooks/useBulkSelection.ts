import { useState, useCallback, useMemo } from "react";
import { Alert } from "react-native";

interface UseBulkSelectionOptions<T> {
  items: T[];
  getItemId: (item: T) => string;
  onDelete: (ids: string[]) => Promise<void>;
  itemName?: string;
}

export function useBulkSelection<T>({
  items,
  getItemId,
  onDelete,
  itemName = "items",
}: UseBulkSelectionOptions<T>) {
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const enterSelectionMode = useCallback(() => {
    setSelectionMode(true);
    setSelectedIds(new Set());
  }, []);

  const exitSelectionMode = useCallback(() => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  }, []);

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === items.length) {
        return new Set();
      }
      return new Set(items.map(getItemId));
    });
  }, [items, getItemId]);

  const selectedCount = selectedIds.size;
  const allSelected = items.length > 0 && selectedCount === items.length;

  const confirmDelete = useCallback(() => {
    if (selectedCount === 0) {
      Alert.alert("No Selection", `Please select at least one ${itemName.slice(0, -1) || itemName}.`);
      return;
    }

    Alert.alert(
      `Delete ${selectedCount} ${selectedCount === 1 ? itemName.slice(0, -1) || itemName : itemName}?`,
      "This action cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeleting(true);
            try {
              await onDelete(Array.from(selectedIds));
              exitSelectionMode();
            } catch (error) {
              Alert.alert("Error", `Failed to delete ${itemName}. Please try again.`);
            } finally {
              setDeleting(false);
            }
          },
        },
      ]
    );
  }, [selectedCount, selectedIds, onDelete, exitSelectionMode, itemName]);

  return useMemo(
    () => ({
      selectionMode,
      selectedIds,
      selectedCount,
      allSelected,
      deleting,
      enterSelectionMode,
      exitSelectionMode,
      toggleSelection,
      toggleAll,
      confirmDelete,
    }),
    [
      selectionMode,
      selectedIds,
      selectedCount,
      allSelected,
      deleting,
      enterSelectionMode,
      exitSelectionMode,
      toggleSelection,
      toggleAll,
      confirmDelete,
    ]
  );
}
