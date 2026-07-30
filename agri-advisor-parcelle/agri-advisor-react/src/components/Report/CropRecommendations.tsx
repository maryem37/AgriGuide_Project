import { useEffect, useRef } from "react";
import { Prose } from "./Prose";
import { parseCropRows } from "./reportParser";

export function CropRecommendations({ body }: { body: string }) {
  const rows = parseCropRows(body);
  const containerRef = useRef<HTMLDivElement>(null);

  // Animate the score bars in on mount, same easing as the original interface.
  useEffect(() => {
    const bars = containerRef.current?.querySelectorAll<HTMLDivElement>("[data-pct]");
    if (!bars) return;
    requestAnimationFrame(() => {
      bars.forEach((bar) => {
        bar.style.width = `${bar.dataset.pct}%`;
      });
    });
  }, [rows.length]);

  if (!rows.length) {
    return <Prose text={body} />;
  }

  return (
    <div ref={containerRef}>
      {rows.map((row, i) => {
        const pct = Math.round(row.score * 100);
        const fillClass = i === 0 ? "fg" : row.score > 0.7 ? "fv" : "fd";
        const rankClass = i === 0 ? "r1" : "";
        return (
          <div className="crec" key={row.name + i}>
            <div className="crec-h">
              <div className="crec-n">
                <div className={`crnk ${rankClass}`}>{i + 1}</div>
                {row.name}
              </div>
              <div className="crsc">{pct}%</div>
            </div>
            {row.reason && (
              <div className="crrz">
                <Prose text={row.reason} className="crrz-prose" />
              </div>
            )}
            <div className="crt">
              <div className={`crf ${fillClass}`} data-pct={pct} style={{ width: 0 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
