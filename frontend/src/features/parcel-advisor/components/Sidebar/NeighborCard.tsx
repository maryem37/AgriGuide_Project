import { useEffect, useRef } from "react";
import type { NeighborCropContext } from "../../types/api";

export function NeighborCard({ neighbors }: { neighbors: NeighborCropContext | null }) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bars = listRef.current?.querySelectorAll<HTMLDivElement>("[data-pct]");
    if (!bars) return;
    requestAnimationFrame(() => {
      bars.forEach((bar) => {
        bar.style.width = `${bar.dataset.pct}%`;
      });
    });
  }, [neighbors]);

  if (!neighbors || !Object.keys(neighbors.crop_distribution_pct).length) return null;

  return (
    <div className="card neighbor-card">
      <h3>Cultures voisines — {neighbors.neighbor_count} parcelles (800 m)</h3>
      <div className="nlist" ref={listRef}>
        {Object.entries(neighbors.crop_distribution_pct).map(([name, pct]) => (
          <div className="cbar" key={name}>
            <div className="cbar-head">
              <span className="cbar-name">{name}</span>
              <span className="cbar-pct">{pct}%</span>
            </div>
            <div className="cbar-track">
              <div className="cbar-fill" data-pct={pct} style={{ width: 0 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
