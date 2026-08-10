import { useState, useCallback } from "react";
import { detectionService } from "../services/detection";
import { Detection } from "../types";

type ImageInput = string | File;

export function useDetection() {
  const [detection, setDetection] = useState<Detection | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(
    async (image: ImageInput, region: string, latitude?: number | null, longitude?: number | null) => {
      setIsAnalyzing(true);
      setError(null);
      try {
        const result = await detectionService.detectInsect(image, region, latitude, longitude);
        setDetection(result);
        return result;
      } catch (err: any) {
        const message =
          err.response?.data?.detail ||
          "Failed to analyze image. Please try again.";
        setError(message);
        throw new Error(message);
      } finally {
        setIsAnalyzing(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setDetection(null);
    setError(null);
  }, []);

  return { detection, isAnalyzing, error, analyze, reset };
}
