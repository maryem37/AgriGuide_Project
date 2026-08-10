import React, { ReactNode } from "react";
import { View, Text, StyleSheet, ViewStyle } from "react-native";

interface CardProps {
  children: ReactNode;
  title?: string;
  style?: ViewStyle;
  variant?: "default" | "elevated" | "outlined";
}

export function Card({
  children,
  title,
  style,
  variant = "default",
}: CardProps) {
  return (
    <View style={[styles.card, styles[variant], style]}>
      {title && <Text style={styles.title}>{title}</Text>}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  default: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  elevated: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 20,
    elevation: 6,
  },
  outlined: {
    borderWidth: 1,
    borderColor: "#E0E0E0",
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: "#212121",
    marginBottom: 12,
  },
});
