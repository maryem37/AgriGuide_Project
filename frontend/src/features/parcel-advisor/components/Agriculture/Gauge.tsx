interface GaugeProps {
  label: string;
  raw: string;
  percent: number;
}

const R = 26;
const CIRC = 2 * Math.PI * R;

function toneFor(percent: number): "good" | "mid" | "low" {
  if (percent >= 65) return "good";
  if (percent >= 40) return "mid";
  return "low";
}

export function Gauge({ label, raw, percent }: GaugeProps) {
  const offset = CIRC - (percent / 100) * CIRC;
  const tone = toneFor(percent);

  return (
    <div className="gauge">
      <svg viewBox="0 0 64 64" className={`gauge-ring gauge-${tone}`}>
        <circle cx="32" cy="32" r={R} className="gauge-track" />
        <circle
          cx="32"
          cy="32"
          r={R}
          className="gauge-fill"
          strokeDasharray={CIRC}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="gauge-text">
        <span className="gauge-val">{raw}</span>
      </div>
      <div className="gauge-label">{label}</div>
    </div>
  );
}
