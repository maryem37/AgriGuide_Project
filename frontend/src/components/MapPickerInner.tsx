import { useEffect, useState } from "react";
import { MapContainer, TileLayer, useMapEvents, Polygon, Marker } from "react-leaflet";
import L from "leaflet";

// Fix default icons
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function Clicker({ onAdd }: { onAdd: (p: [number, number]) => void }) {
  useMapEvents({
    click(e) {
      onAdd([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

export default function MapPickerInner({
  onPolygon,
  height = 480,
}: {
  onPolygon?: (points: [number, number][]) => void;
  height?: number | string;
}) {
  const [points, setPoints] = useState<[number, number][]>([]);

  useEffect(() => {
    onPolygon?.(points);
  }, [points, onPolygon]);

  return (
    <div className="relative">
      <div style={{ height }} className="overflow-hidden rounded-2xl border border-border shadow-soft">
        <MapContainer center={[46.7, 2.5]} zoom={6} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Clicker onAdd={(p) => setPoints((prev) => [...prev, p])} />
          {points.map((p, i) => (
            <Marker key={i} position={p} />
          ))}
          {points.length >= 3 && (
            <Polygon positions={points} pathOptions={{ color: "#3d8f5a", fillColor: "#7fbf95", fillOpacity: 0.35 }} />
          )}
        </MapContainer>
      </div>
      <div className="absolute top-3 left-3 right-3 md:right-auto md:max-w-sm rounded-2xl bg-card/95 backdrop-blur p-3 shadow-soft border border-border pointer-events-none">
        <div className="text-sm font-semibold">Tracez votre terrain</div>
        <p className="text-xs text-muted-foreground mt-1">
          Touchez la carte pour ajouter des points. Un contour se dessine automatiquement dès 3 points.
        </p>
      </div>
      {points.length > 0 && (
        <button
          onClick={() => setPoints([])}
          className="absolute bottom-3 right-3 rounded-xl bg-card border border-border px-3 py-2 text-sm font-medium shadow-soft hover:bg-secondary"
        >
          Effacer
        </button>
      )}
    </div>
  );
}
