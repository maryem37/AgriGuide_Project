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

const EQUIPEMENT_LABELS: Record<EquipementType, string> = Object.fromEntries(
  EQUIPEMENT_OPTIONS.map((o) => [o.value, o.label]),
) as Record<EquipementType, string>;

export function equipementLabel(type: EquipementType): string {
  return EQUIPEMENT_LABELS[type] ?? type;
}
