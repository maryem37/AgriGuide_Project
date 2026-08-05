import { useEffect, useRef } from "react";
// Type-only import: erased at compile time, never evaluated at runtime,
// so this line alone can't break SSR — only the real `import("mapbox-gl")`
// below (which runs exclusively inside a client-only useEffect) can.
import type mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

type PolygonGeometry = { type: "Polygon"; coordinates: number[][][] };
type MultiPolygonGeometry = { type: "MultiPolygon"; coordinates: number[][][][] };

const PARCEL_SOURCE_ID = "parcel-boundary";
const PARCEL_FILL_LAYER_ID = "parcel-boundary-fill";
const PARCEL_LINE_LAYER_ID = "parcel-boundary-line";

export default function TerrainMap3DInner({
  center,
  overlayGeometry,
  height = 480,
  zoom = 16,
  pitch = 60,
  bearing = -20,
}: {
  /** [lat, lon] — same convention MapPickerInner uses; converted to Mapbox's [lng, lat] below. */
  center: [number, number];
  overlayGeometry?: PolygonGeometry | MultiPolygonGeometry | null;
  height?: number | string;
  zoom?: number;
  pitch?: number;
  bearing?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  // Map is created once. Re-flying to a new center/geometry on prop change
  // is handled by the second effect below, rather than tearing the whole
  // map down — that avoids a visible flicker every time the parcel changes.
  //
  // `mapbox-gl` is dynamically imported HERE, not at the top of the file.
  // A static top-level `import mapboxgl from "mapbox-gl"` gets evaluated
  // as part of the module graph during SSR (this app renders server-side
  // via TanStack Start), and mapbox-gl touches window/navigator/WebGL at
  // import time — it is not SSR-safe. That mismatch between what the
  // server could render and what the client actually produced is what
  // was causing the hydration-mismatch crash on /agriculture. A dynamic
  // import() inside a useEffect only ever runs in the browser, after
  // mount, so the module is never touched during the server render at
  // all — same fix pattern as `dynamic(() => import(...), { ssr: false })`
  // in Next.js, applied without a framework helper.
  useEffect(() => {
    if (!containerRef.current) return;
    if (!MAPBOX_TOKEN) {
      console.error(
        "VITE_MAPBOX_TOKEN is not set — add it to the repo root .env. " +
          "See MapPicker's Leaflet view for the 2D fallback in the meantime.",
      );
      return;
    }

    let cancelled = false;
    let map: mapboxgl.Map | null = null;

    import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled || !containerRef.current) return;

      mapboxgl.accessToken = MAPBOX_TOKEN!;

      map = new mapboxgl.Map({
        container: containerRef.current,
        style: "mapbox://styles/mapbox/satellite-streets-v12",
        center: [center[1], center[0]], // Mapbox wants [lng, lat]
        zoom,
        pitch,
        bearing,
        antialias: true, // smoother terrain edges
      });
      mapRef.current = map;

      map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");

      map.on("load", () => {
        if (!map) return;

        // --- 3D terrain (Mapbox's own hosted DEM tileset) ---
        map.addSource("mapbox-dem", {
          type: "raster-dem",
          url: "mapbox://mapbox.mapbox-terrain-dem-v1",
          tileSize: 512,
          maxzoom: 14,
        });
        map.setTerrain({ source: "mapbox-dem", exaggeration: 1.4 });

        // --- Sky layer, purely cosmetic — makes the 3D pitch read as a real landscape rather than a tilted flat photo ---
        map.addLayer({
          id: "sky",
          type: "sky",
          paint: {
            "sky-type": "atmosphere",
            "sky-atmosphere-sun-intensity": 12,
          },
        });

        addOrUpdateParcelLayer(map, overlayGeometry);
      });
    });

    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
    // Intentionally empty dep array — see comment above. center/overlayGeometry
    // changes are handled by the effect below via flyTo + layer update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-center + redraw the parcel boundary whenever the resolved parcel
  // changes, without recreating the whole map (keeps the 3D camera state
  // and avoids a full tile reload flash).
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const fly = () => {
      map.flyTo({ center: [center[1], center[0]], zoom, pitch, bearing, essential: true });
      addOrUpdateParcelLayer(map, overlayGeometry);
    };
    if (map.isStyleLoaded()) fly();
    else map.once("load", fly);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center[0], center[1], JSON.stringify(overlayGeometry)]);

  if (!MAPBOX_TOKEN) {
    return (
      <div
        style={{ height }}
        className="rounded-2xl border border-border bg-secondary/30 flex items-center justify-center text-sm text-muted-foreground p-4 text-center"
      >
        VITE_MAPBOX_TOKEN manquant — ajoutez-le dans le .env à la racine du repo pour activer la vue 3D.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="relative z-0 overflow-hidden rounded-2xl border border-border shadow-soft"
    />
  );
}

function addOrUpdateParcelLayer(
  map: mapboxgl.Map,
  geometry?: PolygonGeometry | MultiPolygonGeometry | null,
) {
  const data: GeoJSON.Feature = {
    type: "Feature",
    properties: {},
    geometry: geometry ?? { type: "Polygon", coordinates: [] },
  };

  const existing = map.getSource(PARCEL_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
  if (existing) {
    existing.setData(data);
    return;
  }
  if (!geometry) return; // nothing to draw yet, and no source to attach layers to

  map.addSource(PARCEL_SOURCE_ID, { type: "geojson", data });
  map.addLayer({
    id: PARCEL_FILL_LAYER_ID,
    type: "fill",
    source: PARCEL_SOURCE_ID,
    paint: { "fill-color": "#7fbf95", "fill-opacity": 0.3 },
  });
  map.addLayer({
    id: PARCEL_LINE_LAYER_ID,
    type: "line",
    source: PARCEL_SOURCE_ID,
    paint: { "line-color": "#2f6f45", "line-width": 2 },
  });
}
