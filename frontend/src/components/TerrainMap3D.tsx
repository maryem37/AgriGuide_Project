import { lazy, Suspense } from "react";

const TerrainMap3DInner = lazy(() => import("./TerrainMap3DInner"));

type PolygonGeometry = { type: "Polygon"; coordinates: number[][][] };
type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: number[][][][] };

export function TerrainMap3D(props: {
  /** [lat, lon] — same coordinate convention as MapPicker, converted to Mapbox's [lng, lat] internally. */
  center: [number, number];
  overlayGeometry?: PolygonGeometry | MultiPolygonGeometry | null;
  height?: number | string;
  zoom?: number;
  pitch?: number;
  bearing?: number;
}) {
  return (
    <Suspense
      fallback={
        <div
          className="rounded-2xl bg-gradient-sky flex items-center justify-center text-sky-foreground"
          style={{ height: props.height ?? 480 }}
        >
          Chargement de la vue 3D…
        </div>
      }
    >
      <TerrainMap3DInner {...props} />
    </Suspense>
  );
}
