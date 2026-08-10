/**
 * Centralized theme and color definitions
 * Single source of truth for all risk level colors and styling
 */

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface RiskConfig {
  color: string;          // Primary color for this risk level
  bg: string;             // Background color (lighter shade)
  icon: "shield-checkmark" | "warning" | "alert-circle" | "skull";  // Icon name
  label: string;          // Display label
}

/**
 * Risk level configuration
 * Used across Map, Detection Cards, Result screens, and Notifications
 */
export const RISK_CONFIGS: Record<RiskLevel, RiskConfig> = {
  low: {
    color: "#4CAF50",
    bg: "#E8F5E9",
    icon: "shield-checkmark",
    label: "Low Risk",
  },
  medium: {
    color: "#FF9800",
    bg: "#FFF3E0",
    icon: "warning",
    label: "Medium Risk",
  },
  high: {
    color: "#F44336",
    bg: "#FFEBEE",
    icon: "alert-circle",
    label: "High Risk",
  },
  critical: {
    color: "#9C27B0",
    bg: "#F3E5F5",
    icon: "skull",
    label: "Critical",
  },
};

/**
 * Get risk configuration by risk level
 * Returns low config as fallback if risk level is unknown
 */
export function getRiskConfig(risk: string | undefined): RiskConfig {
  if (!risk || !(risk in RISK_CONFIGS)) {
    return RISK_CONFIGS.low;
  }
  return RISK_CONFIGS[risk as RiskLevel];
}

/**
 * Get just the color for a risk level
 * Useful for marker colors, badges, etc.
 */
export function getRiskColor(risk: string | undefined): string {
  return getRiskConfig(risk).color;
}

/**
 * Get just the background color for a risk level
 */
export function getRiskBgColor(risk: string | undefined): string {
  return getRiskConfig(risk).bg;
}

/**
 * Get just the label for a risk level
 */
export function getRiskLabel(risk: string | undefined): string {
  return getRiskConfig(risk).label;
}

/**
 * Get just the icon name for a risk level
 */
export function getRiskIcon(risk: string | undefined): "shield-checkmark" | "warning" | "alert-circle" | "skull" {
  return getRiskConfig(risk).icon;
}

/**
 * Risk filter chip configuration for the map filter UI
 */
export const RISK_FILTERS = [
  { key: "all", label: "All", color: "#2E7D32" },
  { key: "low", label: "Low", color: "#4CAF50" },
  { key: "medium", label: "Medium", color: "#FF9800" },
  { key: "high", label: "High", color: "#F44336" },
  { key: "critical", label: "Critical", color: "#9C27B0" },
];

/**
 * Global color scheme
 */
export const COLORS = {
  primary: "#2E7D32",
  secondary: "#4CAF50",
  error: "#F44336",
  warning: "#FF9800",
  info: "#1976D2",
  success: "#4CAF50",
  text: {
    primary: "#212121",
    secondary: "#757575",
    disabled: "#BDBDBD",
  },
  bg: {
    light: "#F8F9FA",
    lighter: "#FFFFFF",
  },
  border: "#E0E0E0",
};
