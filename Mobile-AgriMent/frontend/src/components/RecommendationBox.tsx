import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface RecommendationBoxProps {
  title: string;
  color?: string;
}

function parseContent(text: string): { type: "bullet" | "numbered" | "paragraph"; content: string; number?: string }[] {
  if (text.includes("|")) {
    return text.split("|").filter((s) => s.trim().length > 0).map((item) => ({
      type: "bullet" as const,
      content: item.trim().replace(/^[-•]\s*/, ""),
    }));
  }
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  return lines.map((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
      return { type: "bullet" as const, content: trimmed.replace(/^[-•]\s*/, "") };
    }
    const numMatch = trimmed.match(/^(\d+[\.\)]\s*)/);
    if (numMatch) {
      return { type: "numbered" as const, content: trimmed.replace(/^\d+[\.\)]\s*/, ""), number: numMatch[1].trim().replace(".", "") };
    }
    return { type: "paragraph" as const, content: trimmed };
  });
}

export function RecommendationBox({ title, color = "#2E7D32" }: RecommendationBoxProps) {
  const items = parseContent(title);

  return (
    <View style={styles.container}>
      {items.map((item, i) => {
        if (item.type === "bullet") {
          return (
            <View key={i} style={styles.bulletRow}>
              <View style={[styles.bulletDot, { backgroundColor: color }]} />
              <Text style={styles.bulletText}>{item.content}</Text>
            </View>
          );
        }
        if (item.type === "numbered") {
          return (
            <View key={i} style={styles.bulletRow}>
              <View style={[styles.numberBadge, { backgroundColor: color }]}>
                <Text style={styles.numberText}>{item.number}</Text>
              </View>
              <Text style={styles.bulletText}>{item.content}</Text>
            </View>
          );
        }
        return (
          <Text key={i} style={styles.paragraphText}>
            {item.content}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
  },
  bulletRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  bulletDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginTop: 7,
  },
  bulletText: {
    flex: 1,
    fontSize: 14,
    color: "#424242",
    lineHeight: 22,
  },
  numberBadge: {
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  numberText: {
    color: "#FFF",
    fontSize: 11,
    fontWeight: "700",
  },
  paragraphText: {
    fontSize: 14,
    color: "#616161",
    lineHeight: 22,
  },
});
