import { lazy, Suspense } from "react";

const MapInner = lazy(() => import("./MapPickerInner"));

export function MapPicker(props: {
  onPolygon?: (points: [number, number][]) => void;
  height?: number | string;
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
