import {
  Wheat,
  Sun,
  Leaf,
  Ban,
  Sprout,
  type LucideIcon,
} from "lucide-react";

export type Visual = { icon: LucideIcon; bg: string; fg: string };

/**
 * Maps a crop label (French display name or raw RPG code) to an icon +
 * pastel color pair, purely cosmetic — grouped by rough crop family so the
 * same visual language is reused across the neighbor list, the crop
 * recommendation cards, and the AI report (see ReportMarkdown.tsx).
 */
const RULES: { test: RegExp; visual: Visual }[] = [
  { test: /jach[eè]re/i, visual: { icon: Ban, bg: "oklch(0.93 0.01 90)", fg: "oklch(0.55 0.01 90)" } },
  {
    test: /bl[eé]|orge|avoine|seigle|c[eé]r[eé]ale|ma[iï]s|riz/i,
    visual: { icon: Wheat, bg: "oklch(0.92 0.06 85)", fg: "oklch(0.52 0.1 70)" },
  },
  {
    test: /colza|tournesol|soja|olé|lin\b/i,
    visual: { icon: Sun, bg: "oklch(0.93 0.09 95)", fg: "oklch(0.58 0.14 85)" },
  },
  {
    test: /prairie|luzerne|fourrage|herbe|tre?fle/i,
    visual: { icon: Leaf, bg: "oklch(0.92 0.05 145)", fg: "oklch(0.48 0.1 145)" },
  },
];

const DEFAULT_VISUAL: Visual = { icon: Sprout, bg: "oklch(0.92 0.04 150)", fg: "oklch(0.45 0.1 150)" };

export function getCropVisual(label: string): Visual {
  return RULES.find((r) => r.test.test(label))?.visual ?? DEFAULT_VISUAL;
}

/** Colors a suitability/compatibility score (0-100) from red (weak) to green (strong) for quick scanning. */
export function scoreTone(score: number): { bg: string; fg: string } {
  if (score >= 70) return { bg: "oklch(0.88 0.05 150)", fg: "oklch(0.35 0.08 150)" };
  if (score >= 40) return { bg: "oklch(0.92 0.07 85)", fg: "oklch(0.5 0.1 65)" };
  return { bg: "oklch(0.92 0.06 30)", fg: "oklch(0.5 0.12 25)" };
}
