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

/** Sous-ensemble minimal de GeoJSON (Polygon/MultiPolygon) — évite une dépendance sur les types globaux `@types/geojson`. */
type PolygonGeometry = { type: "Polygon"; coordinates: number[][][] };
type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: number[][][][] };

function Clicker({ onAdd }: { onAdd: (p: [number, number]) => void }) {
  useMapEvents({
    click(e) {
      onAdd([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

export default function MapPickerInner({
  mode = "polygon",
  onPolygon,
  onPoint,
  markerPosition,
  overlayGeometry,
  neighborGeometries,
  height = 480,
  center = [46.7, 2.5],
  zoom = 6,
  hint,
}: {
  /** "polygon" (défaut) : trace un contour libre, comme à l'onboarding.
   *  "point" : un seul clic déplace un marqueur unique — utilisé pour résoudre une parcelle cadastrale précise. */
  mode?: "polygon" | "point";
  onPolygon?: (points: [number, number][]) => void;
  onPoint?: (point: [number, number]) => void;
  /** En mode "point" : position du marqueur pilotée par le parent (ex. resynchronisée après résolution de parcelle). */
  markerPosition?: [number, number] | null;
  /** En mode "point" : polygone GeoJSON à afficher en surimpression (ex. contour cadastral résolu). */
  overlayGeometry?: PolygonGeometry | MultiPolygonGeometry | null;
  /** En mode "point" : parcelles voisines (contexte RPG) à afficher en surimpression, en pointillés orange. */
  neighborGeometries?: (PolygonGeometry | MultiPolygonGeometry)[];
  height?: number | string;
  center?: [number, number];
  zoom?: number;
  hint?: string;
}) {
  const [points, setPoints] = useState<[number, number][]>([]);
  const [point, setPoint] = useState<[number, number] | null>(markerPosition ?? null);

  useEffect(() => {
    if (mode === "polygon") onPolygon?.(points);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, mode]);

  useEffect(() => {
    if (markerPosition !== undefined) setPoint(markerPosition);
  }, [markerPosition]);

  function handleAdd(p: [number, number]) {
    if (mode === "point") {
      setPoint(p);
      onPoint?.(p);
    } else {
      setPoints((prev) => [...prev, p]);
    }
  }

  const overlayPositions = overlayToLatLngRings(overlayGeometry);
  const neighborPositions = (neighborGeometries ?? []).flatMap((g) => overlayToLatLngRings(g));

  return (
    <div className="relative">
      <div style={{ height }} className="overflow-hidden rounded-2xl border border-border shadow-soft">
        <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Clicker onAdd={handleAdd} />
          {mode === "polygon" &&
            points.map((p, i) => <Marker key={i} position={p} />)}
          {mode === "polygon" && points.length >= 3 && (
            <Polygon positions={points} pathOptions={{ color: "#3d8f5a", fillColor: "#7fbf95", fillOpacity: 0.35 }} />
          )}
          {mode === "point" && point && <Marker position={point} />}
          {mode === "point" &&
            neighborPositions.map((ring, i) => (
              <Polygon
                key={`neighbor-${i}`}
                positions={ring}
                pathOptions={{ color: "#e0983c", fillColor: "#e0983c", fillOpacity: 0.08, weight: 1.5, dashArray: "6 6" }}
              />
            ))}
          {mode === "point" &&
            overlayPositions.map((ring, i) => (
              <Polygon
                key={i}
                positions={ring}
                pathOptions={{ color: "#2f6f45", fillColor: "#7fbf95", fillOpacity: 0.3, weight: 2 }}
              />
            ))}
        </MapContainer>
      </div>
      <div className="absolute top-3 left-3 right-3 md:right-auto md:max-w-sm rounded-2xl bg-card/95 backdrop-blur p-3 shadow-soft border border-border pointer-events-none">
        <div className="text-sm font-semibold">{mode === "point" ? "Cliquez sur votre parcelle" : "Tracez votre terrain"}</div>
        <p className="text-xs text-muted-foreground mt-1">
          {hint ??
            (mode === "point"
              ? "Un clic résout la parcelle cadastrale/RPG à cet endroit."
              : "Touchez la carte pour ajouter des points. Un contour se dessine automatiquement dès 3 points.")}
        </p>
      </div>
      {mode === "polygon" && points.length > 0 && (
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

/** Convertit une géométrie GeoJSON Polygon/MultiPolygon en anneaux [lat, lng] pour <Polygon> de react-leaflet (qui attend lat/lng, alors que GeoJSON stocke lng/lat). */
function overlayToLatLngRings(
  geometry?: PolygonGeometry | MultiPolygonGeometry | null,
): [number, number][][] {
  if (!geometry) return [];
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  return polygons.map((rings) => rings[0].map(([lng, lat]) => [lat, lng] as [number, number]));
}
