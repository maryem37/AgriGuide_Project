import { cn } from "@/lib/utils";
import { useCountUp } from "@/components/motion/useCountUp";

export function ScoreGauge({
  value,
  label,
  size = 120,
  tone = "primary",
}: {
  value: number; // 0-100
  label?: string;
  size?: number;
  tone?: "primary" | "earth" | "sky" | "waste";
}) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, value)) / 100) * c;
  const color =
    tone === "earth"
      ? "var(--color-earth)"
      : tone === "sky"
        ? "var(--color-sky)"
        : tone === "waste"
          ? "var(--color-waste)"
          : "var(--color-primary)";

  // Le compteur démarre quand la jauge entre dans le viewport, en phase avec le tracé.
  const [ref, displayed] = useCountUp<HTMLDivElement>(value, { duration: 1100 });

  return (
    <div ref={ref} className="flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90 overflow-visible">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={10}
          stroke="var(--color-muted)"
          fill="none"
        />
        <circle
          className="gauge-arc"
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={10}
          stroke={color}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={
            {
              "--gauge-circumference": c,
              "--gauge-offset": offset,
              filter: `drop-shadow(0 0 6px color-mix(in oklch, ${color} 45%, transparent))`,
            } as React.CSSProperties
          }
        />
      </svg>
      <div
        className={cn("flex flex-col items-center", "pointer-events-none")}
        style={{ marginTop: -(size / 2 + 12) }}
      >
        <div className="font-display text-2xl font-semibold tabular-nums">{displayed}</div>
        {label && <div className="text-xs text-muted-foreground">{label}</div>}
      </div>
      <div style={{ height: size / 2 - 12 }} />
    </div>
  );
}
