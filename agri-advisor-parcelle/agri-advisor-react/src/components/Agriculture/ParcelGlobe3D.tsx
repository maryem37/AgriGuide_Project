import { useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import {
  Bounds,
  ContactShadows,
  Environment,
  Grid,
  OrbitControls,
} from "@react-three/drei";
import * as THREE from "three";

interface PolygonGeometry {
  type: "Polygon";
  coordinates: number[][][];
}

interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: number[][][][];
}

export type GeoJsonGeometry = PolygonGeometry | MultiPolygonGeometry;

interface Parcel3DViewProps {
  geometry: GeoJsonGeometry;
  onClose: () => void;
}

function ringArea(ring: number[][]): number {
  if (ring.length < 3) {
    return 0;
  }

  let area = 0;

  for (let index = 0; index < ring.length; index += 1) {
    const current = ring[index];
    const next = ring[(index + 1) % ring.length];

    area += current[0] * next[1] - next[0] * current[1];
  }

  return Math.abs(area / 2);
}

function extractMainRing(geometry: GeoJsonGeometry): number[][] {
  if (geometry.type === "Polygon") {
    return geometry.coordinates[0] ?? [];
  }

  let largestRing: number[][] = [];
  let largestArea = 0;

  geometry.coordinates.forEach((polygon) => {
    const exteriorRing = polygon[0] ?? [];
    const area = ringArea(exteriorRing);

    if (area > largestArea) {
      largestArea = area;
      largestRing = exteriorRing;
    }
  });

  return largestRing;
}

function removeDuplicateClosingPoint(coordinates: number[][]): number[][] {
  if (coordinates.length < 2) {
    return coordinates;
  }

  const first = coordinates[0];
  const last = coordinates[coordinates.length - 1];

  const isClosed =
    first[0] === last[0] &&
    first[1] === last[1];

  return isClosed ? coordinates.slice(0, -1) : coordinates;
}

function normalizeCoordinates(coordinates: number[][]): THREE.Vector2[] {
  const cleanedCoordinates = removeDuplicateClosingPoint(coordinates);

  if (cleanedCoordinates.length < 3) {
    return [];
  }

  const centerLongitude =
    cleanedCoordinates.reduce(
      (sum, coordinate) => sum + coordinate[0],
      0,
    ) / cleanedCoordinates.length;

  const centerLatitude =
    cleanedCoordinates.reduce(
      (sum, coordinate) => sum + coordinate[1],
      0,
    ) / cleanedCoordinates.length;

  const latitudeCorrection = Math.cos(
    (centerLatitude * Math.PI) / 180,
  );

  const coordinatesInMeters = cleanedCoordinates.map(
    ([longitude, latitude]) => ({
      x:
        (longitude - centerLongitude) *
        111_320 *
        latitudeCorrection,
      y:
        (latitude - centerLatitude) *
        110_540,
    }),
  );

  const maxDistance = Math.max(
    ...coordinatesInMeters.map(({ x, y }) =>
      Math.max(Math.abs(x), Math.abs(y)),
    ),
    1,
  );

  const targetSize = 8;
  const scale = targetSize / maxDistance;

  return coordinatesInMeters.map(
    ({ x, y }) =>
      new THREE.Vector2(
        x * scale,
        y * scale,
      ),
  );
}

function ParcelMesh({
  geometry,
}: {
  geometry: GeoJsonGeometry;
}) {
  const parcelGeometry = useMemo(() => {
    const mainRing = extractMainRing(geometry);
    const normalizedPoints = normalizeCoordinates(mainRing);

    if (normalizedPoints.length < 3) {
      return null;
    }

    const shape = new THREE.Shape();

    shape.moveTo(
      normalizedPoints[0].x,
      normalizedPoints[0].y,
    );

    normalizedPoints.slice(1).forEach((point) => {
      shape.lineTo(point.x, point.y);
    });

    shape.closePath();

    const extrusionSettings: THREE.ExtrudeGeometryOptions = {
      depth: 0.65,
      bevelEnabled: true,
      bevelThickness: 0.06,
      bevelSize: 0.06,
      bevelOffset: 0,
      bevelSegments: 3,
      curveSegments: 12,
      steps: 1,
    };

    const result = new THREE.ExtrudeGeometry(
      shape,
      extrusionSettings,
    );

    result.center();
    result.computeVertexNormals();
    result.computeBoundingBox();

    return result;
  }, [geometry]);

  useEffect(() => {
    return () => {
      parcelGeometry?.dispose();
    };
  }, [parcelGeometry]);

  if (!parcelGeometry) {
    return null;
  }

  return (
    <mesh
      geometry={parcelGeometry}
      rotation={[-Math.PI / 2, 0, 0]}
      castShadow
      receiveShadow
    >
      <meshStandardMaterial
        color="#22c55e"
        roughness={0.72}
        metalness={0.02}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function Scene({
  geometry,
}: {
  geometry: GeoJsonGeometry;
}) {
  return (
    <>
      <color
        attach="background"
        args={["#eaf5ed"]}
      />

      <ambientLight intensity={1.2} />

      <hemisphereLight
        args={[
          "#ffffff",
          "#6b8f71",
          1.2,
        ]}
      />

      <directionalLight
        position={[8, 14, 8]}
        intensity={2.1}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-near={0.1}
        shadow-camera-far={60}
        shadow-camera-left={-15}
        shadow-camera-right={15}
        shadow-camera-top={15}
        shadow-camera-bottom={-15}
      />

      <Bounds
        fit
        clip
        observe
        margin={1.4}
      >
        <ParcelMesh geometry={geometry} />
      </Bounds>

      <Grid
        position={[0, -0.42, 0]}
        args={[30, 30]}
        cellSize={1}
        cellThickness={0.65}
        cellColor="#a4bda8"
        sectionSize={5}
        sectionThickness={1.1}
        sectionColor="#608269"
        fadeDistance={30}
        fadeStrength={1}
        infiniteGrid
      />

      <ContactShadows
        position={[0, -0.4, 0]}
        opacity={0.32}
        scale={28}
        blur={2.5}
        far={15}
      />

      <Environment preset="park" />

      <OrbitControls
        makeDefault
        enableRotate
        enablePan
        enableZoom
        enableDamping
        dampingFactor={0.08}
        minDistance={4}
        maxDistance={32}
        minPolarAngle={0.15}
        maxPolarAngle={Math.PI / 2.03}
      />
    </>
  );
}

export function Parcel3DView({
  geometry,
  onClose,
}: Parcel3DViewProps) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener(
        "keydown",
        handleKeyDown,
      );
    };
  }, [onClose]);

  return (
    <div
      className="parcel-3d-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="parcel-3d-title"
    >
      <div className="parcel-3d-window">
        <header className="parcel-3d-header">
          <div>
            <span className="parcel-3d-eyebrow">
              Visualisation cadastrale
            </span>

            <h2 id="parcel-3d-title">
              Vue 3D de la parcelle
            </h2>

            <p>
              Faites glisser pour tourner la parcelle et utilisez la
              molette pour zoomer.
            </p>
          </div>

          <button
            type="button"
            className="parcel-3d-close"
            onClick={onClose}
            aria-label="Fermer la vue 3D"
          >
            ×
          </button>
        </header>

        <div className="parcel-3d-canvas">
          <Canvas
            shadows
            dpr={[1, 2]}
            gl={{
              antialias: true,
              alpha: false,
              powerPreference: "high-performance",
            }}
            camera={{
              position: [10, 10, 12],
              fov: 42,
              near: 0.1,
              far: 1000,
            }}
          >
            <Scene geometry={geometry} />
          </Canvas>
        </div>

        <footer className="parcel-3d-footer">
          <span>🖱️ Glisser : rotation</span>
          <span>🔍 Molette : zoom</span>
          <span>✋ Clic droit : déplacement</span>
        </footer>
      </div>
    </div>
  );
}