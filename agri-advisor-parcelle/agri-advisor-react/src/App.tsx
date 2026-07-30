import { useCallback, useState } from "react";
import { ApiError, getNdviHeatmap } from "./api/client";
import { AgricultureDashboard } from "./components/Agriculture/AgricultureDashboard";
import { Chatbot } from "./components/Chatbot/Chatbot";
import { MapView } from "./components/MapView";
import { NavRail, type AppView } from "./components/NavRail/NavRail";
import { ReportModal } from "./components/Report/ReportModal";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { useAdvise } from "./hooks/useAdvise";
import { useParcelSelection } from "./hooks/useParcelSelection";
import type { NdviHeatmapResponse } from "./types/api";

export default function App() {
  const [view, setView] = useState<AppView>("carte");
  const { point, parcel, neighbors, status, message, selectPoint } = useParcelSelection();
  const { report, loading: adviseLoading, error: adviseError, runAdvise, reset: resetAdvise } = useAdvise();

  const [ndviOverlay, setNdviOverlay] = useState<NdviHeatmapResponse | null>(null);
  const [ndviLoading, setNdviLoading] = useState(false);

  const handleSelectPoint = useCallback(
    (lat: number, lon: number) => {
      setNdviOverlay(null);
      selectPoint(lat, lon);
    },
    [selectPoint],
  );

  const handleToggleNdvi = useCallback(async () => {
    if (ndviOverlay) {
      setNdviOverlay(null);
      return;
    }
    if (!point) return;

    setNdviLoading(true);
    try {
      const result = await getNdviHeatmap(point);
      setNdviOverlay(result);
    } catch (err) {
      // Non-critical, descriptive-only layer — surface via console, don't
      // block the main flow the way a failed /advise call would.
      console.error(err instanceof ApiError ? err.message : err);
    } finally {
      setNdviLoading(false);
    }
  }, [ndviOverlay, point]);

  const handleAdvise = useCallback(() => {
    if (point) runAdvise(point);
  }, [point, runAdvise]);

  return (
    <>
      <NavRail active={view} onSelect={setView} />

      <Chatbot
        parcel={parcel}
        neighbors={neighbors}
        reportMarkdown={report?.report_markdown ?? null}
        ndviAvailable={ndviOverlay !== null}
      />

      {view === "carte" && (
        <>
          <MapView
            parcelGeometry={parcel?.geometry ?? null}
            neighborGeometries={neighbors?.neighbors.map((n) => n.geometry) ?? []}
            ndviOverlay={ndviOverlay}
            onSelectPoint={handleSelectPoint}
          />

          <Sidebar
            status={status}
            message={message}
            parcel={parcel}
            neighbors={neighbors}
            ndviAvailable={parcel !== null}
            ndviActive={ndviOverlay !== null}
            ndviLoading={ndviLoading}
            adviseLoading={adviseLoading}
            onToggleNdvi={handleToggleNdvi}
            onAdvise={handleAdvise}
          />

          <ReportModal report={report} loading={adviseLoading} error={adviseError} onClose={resetAdvise} />
        </>
      )}

      {view === "agriculture" && (
        <div className="agri-page">
          <AgricultureDashboard
            parcel={parcel}
            report={report}
            loading={adviseLoading}
            error={adviseError}
            ndviOverlay={ndviOverlay}
            ndviLoading={ndviLoading}
            onRequestNdvi={handleToggleNdvi}
            onAdvise={handleAdvise}
            onGoToMap={() => setView("carte")}
          />
        </div>
      )}
    </>
  );
}
