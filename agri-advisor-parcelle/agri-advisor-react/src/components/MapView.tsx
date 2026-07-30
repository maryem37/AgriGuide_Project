import L from "leaflet";
import { useEffect } from "react";
import { GeoJSON, ImageOverlay, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { GeoJsonGeometry, NdviHeatmapResponse } from "../types/api";
import "./MapView.css";

interface MapViewProps {
  parcelGeometry: GeoJsonGeometry | null;
  neighborGeometries: GeoJsonGeometry[];
  ndviOverlay: NdviHeatmapResponse | null;
  onSelectPoint: (lat: number, lon: number) => void;
}

function ClickHandler({ onSelect }: { onSelect: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/** Fits the map view to the resolved parcel's bounds whenever its geometry changes. */
function FitToGeometry({ geometry }: { geometry: GeoJsonGeometry }) {
  const map = useMap();
  useEffect(() => {
    const layer = L.geoJSON(geometry as GeoJSON.GeoJsonObject);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { maxZoom: 17 });
  }, [geometry, map]);
  return null;
}

export function MapView({ parcelGeometry, neighborGeometries, ndviOverlay, onSelectPoint }: MapViewProps) {
  return (
    <MapContainer center={[46.6, 2.5]} zoom={6} className="map-container" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />

      <ClickHandler onSelect={onSelectPoint} />

      {parcelGeometry && (
        <>
          <GeoJSON
            key={`parcel-${JSON.stringify(parcelGeometry)}`}
            data={parcelGeometry as GeoJSON.GeoJsonObject}
            style={() => ({ color: "#16a34a", weight: 3, fillColor: "#22c55e", fillOpacity: 0.18 })}
          />
          <FitToGeometry geometry={parcelGeometry} />
        </>
      )}

      {neighborGeometries.length > 0 && (
        <GeoJSON
          key={`neighbors-${neighborGeometries.length}`}
          data={
            {
              type: "FeatureCollection",
              features: neighborGeometries.map((geometry) => ({
                type: "Feature",
                properties: {},
                geometry,
              })),
            } as GeoJSON.GeoJsonObject
          }
          style={() => ({ color: "#e65100", weight: 1, fillOpacity: 0.08, dashArray: "4" })}
        />
      )}

      {ndviOverlay && (
        <ImageOverlay
          url={`data:image/png;base64,${ndviOverlay.image_base64}`}
          bounds={[
            [ndviOverlay.bounds.south, ndviOverlay.bounds.west],
            [ndviOverlay.bounds.north, ndviOverlay.bounds.east],
          ]}
          opacity={0.8}
        />
      )}
    </MapContainer>
  );
}
