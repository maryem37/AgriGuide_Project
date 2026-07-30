import { useCallback, useState } from "react";
import { advise, ApiError } from "../api/client";
import type { AdvisorReport, Coordinate } from "../types/api";

interface UseAdviseResult {
  report: AdvisorReport | null;
  loading: boolean;
  error: string | null;
  runAdvise: (point: Coordinate) => Promise<void>;
  reset: () => void;
}

export function useAdvise(): UseAdviseResult {
  const [report, setReport] = useState<AdvisorReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAdvise = useCallback(async (point: Coordinate) => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const result = await advise(point);
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur réseau lors de la génération du rapport.");
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setReport(null);
    setError(null);
  }, []);

  return { report, loading, error, runAdvise, reset };
}
