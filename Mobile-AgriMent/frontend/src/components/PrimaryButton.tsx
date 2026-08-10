import React from "react";
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
} from "react-native";

interface PrimaryButtonProps {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
}

export function PrimaryButton({
  title,
  onPress,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  style,
}: PrimaryButtonProps) {
  const buttonStyles = [
    styles.button,
    styles[variant],
    styles[`size_${size}`],
    disabled && styles.disabled,
    style,
  ];

  const textStyles = [
    styles.text,
    styles[`${variant}_text`],
    styles[`text_${size}`],
  ];

  return (
    <TouchableOpacity
      style={buttonStyles}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.8}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" size="small" />
      ) : (
        <Text style={textStyles}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  primary: { backgroundColor: "#2E7D32" },
  secondary: { backgroundColor: "#4CAF50" },
  outline: {
    backgroundColor: "transparent",
    borderWidth: 2,
    borderColor: "#2E7D32",
  },
  danger: { backgroundColor: "#D32F2F" },
  size_sm: { paddingVertical: 10, paddingHorizontal: 20 },
  size_md: { paddingVertical: 14, paddingHorizontal: 28 },
  size_lg: { paddingVertical: 18, paddingHorizontal: 36 },
  disabled: { opacity: 0.5 },
  text: { fontWeight: "700", textAlign: "center" },
  primary_text: { color: "#FFFFFF" },
  secondary_text: { color: "#FFFFFF" },
  outline_text: { color: "#2E7D32" },
  danger_text: { color: "#FFFFFF" },
  text_sm: { fontSize: 14 },
  text_md: { fontSize: 16 },
  text_lg: { fontSize: 18 },
});
