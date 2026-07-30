import { lazy, Suspense } from "react";

const MapInner = lazy(() => import("./MapPickerInner"));

type PolygonGeometry = { type: "Polygon"; coordinates: number[][][] };
type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: number[][][][] };

export function MapPicker(props: {
  mode?: "polygon" | "point";
  onPolygon?: (points: [number, number][]) => void;
  onPoint?: (point: [number, number]) => void;
  markerPosition?: [number, number] | null;
  overlayGeometry?: PolygonGeometry | MultiPolygonGeometry | null;
  height?: number | string;
  center?: [number, number];
  zoom?: number;
  hint?: string;
}) {
  return (
    <Suspense
      fallback={
        <div
          className="rounded-2xl bg-gradient-sky flex items-center justify-center text-sky-foreground"
          style={{ height: props.height ?? 480 }}
        >
          Chargement de la carte…
        </div>
      }
    >
      <MapInner {...props} />
    </Suspense>
  );
}
