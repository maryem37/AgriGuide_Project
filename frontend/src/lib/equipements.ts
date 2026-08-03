/**
 * Matériel agricole proposé au sign up (case à cocher par type de matériel
 * détenu). Icônes génériques en attendant les vraies images — voir
 * `backend/auth/README.md`.
 */

import {
  Tractor,
  Wrench,
  CircleDot,
  Sprout,
  Wheat,
  Truck,
  SprayCan,
  Warehouse,
  type LucideIcon,
} from "lucide-react";
import type { EquipementType } from "@/lib/authApi";

export const EQUIPEMENT_OPTIONS: { value: EquipementType; label: string; icon: LucideIcon }[] = [
  { value: "tracteur", label: "Tracteur", icon: Tractor },
  { value: "cultivateur", label: "Cultivateur", icon: Wrench },
  { value: "fraise_rotative", label: "Fraise rotative", icon: CircleDot },
  { value: "planteuse", label: "Planteuse", icon: Sprout },
  { value: "moissonneuse_batteuse", label: "Moissonneuse-batteuse", icon: Wheat },
  { value: "remorque_agricole", label: "Remorques agricoles", icon: Truck },
  { value: "pulverisateur", label: "Pulvérisateur", icon: SprayCan },
  { value: "tunnel_plastique", label: "Tunnels plastiques", icon: Warehouse },
];

const EQUIPEMENT_LABELS: Record<string, string> = Object.fromEntries(
  EQUIPEMENT_OPTIONS.map((o) => [o.value, o.label]),
);

/** Normalise un libellé libre vers une clé stockable (aligné backend auth). */
export function slugifyEquipement(label: string): EquipementType | null {
  const cleaned = label
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (cleaned.length < 2 || cleaned.length > 50) return null;
  return cleaned;
}

export function equipementLabel(type: EquipementType): string {
  if (EQUIPEMENT_LABELS[type]) return EQUIPEMENT_LABELS[type];
  return type
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
