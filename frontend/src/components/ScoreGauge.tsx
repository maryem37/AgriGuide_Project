import { cn } from "@/lib/utils";

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
  const offset = c - (value / 100) * c;
  const color =
    tone === "earth" ? "var(--color-earth)" :
    tone === "sky" ? "var(--color-sky)" :
    tone === "waste" ? "var(--color-waste)" :
    "var(--color-primary)";
  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={10} stroke="var(--color-muted)" fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} strokeWidth={10}
          stroke={color} fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset .8s ease" }}
        />
      </svg>
      <div className={cn("-mt-[calc(50%+8px)] flex flex-col items-center", "pointer-events-none")}
        style={{ marginTop: -(size / 2 + 12) }}>
        <div className="font-display text-2xl font-semibold">{value}</div>
        {label && <div className="text-xs text-muted-foreground">{label}</div>}
      </div>
      <div style={{ height: size / 2 - 12 }} />
    </div>
  );
}
