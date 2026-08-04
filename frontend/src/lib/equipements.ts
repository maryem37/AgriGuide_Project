/**
 * Matériel agricole proposé au sign up (case à cocher par type de matériel
 * détenu). Chaque option porte une vraie photo (`public/img/tools/<value>.*`)
 * et une icône de repli — voir `backend/auth/README.md`.
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

export const EQUIPEMENT_OPTIONS: {
  value: EquipementType;
  label: string;
  icon: LucideIcon;
  image: string;
}[] = [
  { value: "tracteur", label: "Tracteur", icon: Tractor, image: "/img/tools/tracteur.webp" },
  {
    value: "cultivateur",
    label: "Cultivateur",
    icon: Wrench,
    image: "/img/tools/cultivateur.webp",
  },
  {
    value: "fraise_rotative",
    label: "Fraise rotative",
    icon: CircleDot,
    image: "/img/tools/fraise_rotative.jpg",
  },
  { value: "planteuse", label: "Planteuse", icon: Sprout, image: "/img/tools/planteuse.webp" },
  {
    value: "moissonneuse_batteuse",
    label: "Moissonneuse-batteuse",
    icon: Wheat,
    image: "/img/tools/moissonneuse_batteuse.webp",
  },
  {
    value: "remorque_agricole",
    label: "Remorques agricoles",
    icon: Truck,
    image: "/img/tools/remorque_agricole.jpg",
  },
  {
    value: "pulverisateur",
    label: "Pulvérisateur",
    icon: SprayCan,
    image: "/img/tools/pulverisateur.jpg",
  },
  {
    value: "tunnel_plastique",
    label: "Tunnels plastiques",
    icon: Warehouse,
    image: "/img/tools/tunnel_plastique.webp",
  },
];

const EQUIPEMENT_LABELS: Record<string, string> = Object.fromEntries(
  EQUIPEMENT_OPTIONS.map((o) => [o.value, o.label]),
);

const EQUIPEMENT_IMAGES: Record<string, string> = Object.fromEntries(
  EQUIPEMENT_OPTIONS.map((o) => [o.value, o.image]),
);

/** Photo du matériel, ou `null` pour un type libre saisi par l'utilisateur. */
export function equipementImage(type: EquipementType): string | null {
  return EQUIPEMENT_IMAGES[type] ?? null;
}

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
