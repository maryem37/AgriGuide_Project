import { useCallback, useState } from "react";
import { ApiError, getNeighbors, resolveParcel } from "../api/client";
import type { Coordinate, NeighborCropContext, ParcelResolution } from "../types/api";

export type SelectionStatus = "idle" | "loading" | "ready" | "error";

interface UseParcelSelectionResult {
  point: Coordinate | null;
  parcel: ParcelResolution | null;
  neighbors: NeighborCropContext | null;
  status: SelectionStatus;
  message: string;
  selectPoint: (lat: number, lon: number) => Promise<void>;
}

const IDLE_MESSAGE = "Cliquez sur la carte pour sélectionner une parcelle.";

export function useParcelSelection(): UseParcelSelectionResult {
  const [point, setPoint] = useState<Coordinate | null>(null);
  const [parcel, setParcel] = useState<ParcelResolution | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborCropContext | null>(null);
  const [status, setStatus] = useState<SelectionStatus>("idle");
  const [message, setMessage] = useState(IDLE_MESSAGE);

  const selectPoint = useCallback(async (lat: number, lon: number) => {
    const p: Coordinate = { lat, lon };
    setPoint(p);
    setParcel(null);
    setNeighbors(null);
    setStatus("loading");
    setMessage(`Recherche à ${lat.toFixed(4)}, ${lon.toFixed(4)}…`);

    try {
      const resolved = await resolveParcel(p);
      if (!resolved.resolved || !resolved.geometry) {
        setStatus("error");
        setMessage(resolved.warning || "Aucune parcelle trouvée à cet endroit.");
        return;
      }

      setParcel(resolved);
      setStatus("ready");

      // Neighbor context is supporting information, not critical — a failure
      // here shouldn't block the user from getting a report on the main parcel.
      try {
        const neighborData = await getNeighbors(p);
        setNeighbors(neighborData);
      } catch {
        setNeighbors(null);
      }
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof ApiError ? err.message : "Erreur réseau lors de la recherche.");
    }
  }, []);

  return { point, parcel, neighbors, status, message, selectPoint };
}
