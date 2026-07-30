import { useCallback, useState } from "react";

import { ApiError, getNdviHeatmap } from "./api/client";
import { AgricultureDashboard } from "./components/Agriculture/AgricultureDashboard";
import { Chatbot } from "./components/Chatbot/Chatbot";
import { MapView } from "./components/MapView";
import {
  NavRail,
  type AppView,
} from "./components/NavRail/NavRail";
import { ReportModal } from "./components/Report/ReportModal";
import { Sidebar } from "./components/Sidebar/Sidebar";

import { useAdvise } from "./hooks/useAdvise";
import { useParcelSelection } from "./hooks/useParcelSelection";

import type { NdviHeatmapResponse } from "./types/api";

export default function ParcelAdvisorApp() {
  /* =========================================================
     VIEW
     ========================================================= */

  const [view, setView] = useState<AppView>("carte");

  /* =========================================================
     PARCEL SELECTION
     ========================================================= */

  const {
    point,
    parcel,
    neighbors,
    status,
    message,
    selectPoint,
  } = useParcelSelection();

  /* =========================================================
     AGRICULTURAL ADVISOR
     ========================================================= */

  const {
    report,
    loading: adviseLoading,
    error: adviseError,
    runAdvise,
    reset: resetAdvise,
  } = useAdvise();

  /* =========================================================
     NDVI
     ========================================================= */

  const [ndviOverlay, setNdviOverlay] =
    useState<NdviHeatmapResponse | null>(null);

  const [ndviLoading, setNdviLoading] = useState(false);

  /* =========================================================
     SELECT PARCEL / POINT
     ========================================================= */

  const handleSelectPoint = useCallback(
    (lat: number, lon: number) => {
      // Reset NDVI when another parcel is selected
      setNdviOverlay(null);

      // Select the new point / parcel
      selectPoint(lat, lon);
    },
    [selectPoint],
  );

  /* =========================================================
     TOGGLE NDVI
     ========================================================= */

  const handleToggleNdvi = useCallback(async () => {
    /*
     * If NDVI is already displayed,
     * hide it.
     */
    if (ndviOverlay) {
      setNdviOverlay(null);
      return;
    }

    /*
     * We need a selected point
     * before requesting NDVI.
     */
    if (!point) {
      return;
    }

    setNdviLoading(true);

    try {
      /*
       * Request NDVI from backend
       */
      const result = await getNdviHeatmap(point);

      /*
       * Display NDVI layer
       */
      setNdviOverlay(result);
    } catch (err) {
      /*
       * NDVI is an optional layer.
       * A failure should not block the rest
       * of the application.
       */
      console.error(
        err instanceof ApiError
          ? err.message
          : err,
      );
    } finally {
      setNdviLoading(false);
    }
  }, [ndviOverlay, point]);

  /* =========================================================
     AGRICULTURAL ADVICE
     ========================================================= */

  const handleAdvise = useCallback(() => {
    /*
     * We need a selected point / parcel
     * before requesting agricultural advice.
     */
    if (!point) {
      return;
    }

    runAdvise(point);
  }, [point, runAdvise]);

  /* =========================================================
     RENDER
     ========================================================= */

  return (
    <>
      {/* =====================================================
          LEFT NAVIGATION
          ===================================================== */}

      <NavRail
        active={view}
        onSelect={setView}
      />

      {/* =====================================================
          CHATBOT
          ===================================================== */}

      <Chatbot
        parcel={parcel}
        neighbors={neighbors}
        reportMarkdown={
          report?.report_markdown ?? null
        }
        ndviAvailable={
          ndviOverlay !== null
        }
      />

      {/* =====================================================
          MAP VIEW
          ===================================================== */}

      {view === "carte" && (
        <>
          <MapView
            parcelGeometry={
              parcel?.geometry ?? null
            }
            neighborGeometries={
              neighbors?.neighbors.map(
                (neighbor) =>
                  neighbor.geometry,
              ) ?? []
            }
            ndviOverlay={ndviOverlay}
            onSelectPoint={handleSelectPoint}
          />

          {/* =================================================
              RIGHT SIDEBAR
              ================================================= */}

          <Sidebar
            status={status}
            message={message}
            parcel={parcel}
            neighbors={neighbors}
            ndviAvailable={
              parcel !== null
            }
            ndviActive={
              ndviOverlay !== null
            }
            ndviLoading={
              ndviLoading
            }
            adviseLoading={
              adviseLoading
            }
            onToggleNdvi={
              handleToggleNdvi
            }
            onAdvise={
              handleAdvise
            }
          />

          {/* =================================================
              AGRICULTURAL REPORT
              ================================================= */}

          <ReportModal
            report={report}
            loading={adviseLoading}
            error={adviseError}
            onClose={resetAdvise}
          />
        </>
      )}

      {/* =====================================================
          AGRICULTURE PAGE
          ===================================================== */}

      {view === "agriculture" && (
        <div className="agri-page">
          <AgricultureDashboard
            parcel={parcel}
            report={report}
            loading={adviseLoading}
            error={adviseError}
            ndviOverlay={ndviOverlay}
            ndviLoading={ndviLoading}
            onRequestNdvi={
              handleToggleNdvi
            }
            onAdvise={
              handleAdvise
            }
            onGoToMap={() =>
              setView("carte")
            }
          />
        </div>
      )}
    </>
  );
}