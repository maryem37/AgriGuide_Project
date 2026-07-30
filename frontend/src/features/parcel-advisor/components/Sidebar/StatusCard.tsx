import type { SelectionStatus } from "../../hooks/useParcelSelection";
import type { ParcelResolution } from "../../types/api";

const SOURCE_LABELS: Record<ParcelResolution["source"], string> = {
  cadastre: "Cadastre (IGN)",
  rpg: "RPG (ASP)",
  manual: "Manuel",
  unresolved: "Non résolu",
};

interface StatusCardProps {
  status: SelectionStatus;
  message: string;
  parcel: ParcelResolution | null;
}

export function StatusCard({ status, message, parcel }: StatusCardProps) {
  const dotClass = status === "ready" ? "active" : status === "error" ? "err" : "";

  return (
    <div className="card status-card">
      {!parcel && (
        <div className="hint">
          <div className={`dot ${dotClass}`} />
          <span>{message}</span>
        </div>
      )}

      {parcel && (
        <div className="parcel-info">
          <div className="pid">{parcel.parcel_id ? `Réf. ${parcel.parcel_id}` : "Parcelle sélectionnée"}</div>

          <div className="irow">
            <span className="ilbl">📍 Source</span>
            <span className="ival">{SOURCE_LABELS[parcel.source] ?? parcel.source}</span>
          </div>

          <div className="irow">
            <span className="ilbl">🌱 Statut</span>
            <span
              className={`badge ${
                parcel.is_agricultural === true ? "bg" : parcel.is_agricultural === false ? "br" : "bd"
              }`}
            >
              {parcel.is_agricultural === true
                ? "✓ Terre agricole (RPG)"
                : parcel.is_agricultural === false
                  ? "⚠️ Non déclarée RPG"
                  : "Statut inconnu"}
            </span>
          </div>

          {parcel.crop_declared && (
            <div className="irow">
              <span className="ilbl">🌿 Culture</span>
              <span className="ival">{parcel.crop_declared}</span>
            </div>
          )}

          {parcel.area_ha != null && (
            <div className="irow">
              <span className="ilbl">📐 Surface</span>
              <span className="ival">{parcel.area_ha.toFixed(2)} ha</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
