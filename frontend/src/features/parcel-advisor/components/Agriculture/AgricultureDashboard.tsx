import type { AdvisorReport, NdviHeatmapResponse, ParcelResolution } from "../../types/api";
import { Prose } from "../Report/Prose";
import { extractSoilGauges, parseCropRows, parseSections } from "../Report/reportParser";
import { Gauge } from "./Gauge";
import "./Agriculture.css";

interface AgricultureDashboardProps {
  parcel: ParcelResolution | null;
  report: AdvisorReport | null;
  loading: boolean;
  error: string | null;
  ndviOverlay: NdviHeatmapResponse | null;
  ndviLoading: boolean;
  onRequestNdvi: () => void;
  onAdvise: () => void;
  onGoToMap: () => void;
}

export function AgricultureDashboard({
  parcel,
  report,
  loading,
  error,
  ndviOverlay,
  ndviLoading,
  onRequestNdvi,
  onAdvise,
  onGoToMap,
}: AgricultureDashboardProps) {
  const sections = report ? parseSections(report.report_markdown) : [];
  const soilSection = sections.find((s) => s.type === "soil");
  const vegSection = sections.find((s) => s.type === "vegetation");
  const cropsSection = sections.find((s) => s.type === "crops");

  const gauges = soilSection ? extractSoilGauges(soilSection.body) : [];
  const cropRows = cropsSection ? parseCropRows(cropsSection.body).slice(0, 5) : [];
  const year = new Date().getFullYear();

  return (
    <div className="agri-dash">
      <div className="agri-dash-head">
        <div className="agri-eyebrow">Conseiller Agriculture</div>
        <h1>Ce que votre terre veut vous dire</h1>
        <p className="agri-sub">
          Analyse croisée du sol, des images satellite et du RPG pour proposer les cultures les plus prometteuses.
        </p>
      </div>

      {!parcel && !loading && (
        <div className="agri-empty">
          <div className="agri-empty-icon">🗺️</div>
          <h2>Sélectionnez d'abord une parcelle</h2>
          <p>Choisissez une parcelle sur la carte, puis lancez l'analyse pour voir apparaître ce tableau de bord.</p>
          <button className="abtn agri-empty-btn" onClick={onGoToMap}>
            📍 Aller sur la carte
          </button>
        </div>
      )}

      {parcel && !report && !loading && !error && (
        <div className="agri-empty">
          <div className="agri-empty-icon">🌾</div>
          <h2>Parcelle prête pour l'analyse</h2>
          <p>Lancez l'analyse agronomique de la parcelle sélectionnée pour voir le sol, le NDVI et les cultures recommandées.</p>
          <button className="abtn agri-empty-btn" onClick={onAdvise}>
            🔍 Obtenir les recommandations
          </button>
        </div>
      )}

      {loading && (
        <div className="agri-empty">
          <div className="spin" />
          <p>Analyse en cours — génération du rapport…</p>
        </div>
      )}

      {error && !loading && (
        <div className="rsec rsec-warn">
          <div className="rsh">
            <div className="sico ico-x">❌</div>
            <div className="stit">Erreur</div>
          </div>
          <Prose text={error} />
        </div>
      )}

      {report && !loading && (
        <>
          <div className="agri-grid-3">
            <div className="agri-card">
              <div className="agri-card-h">Analyse du sol</div>
              {gauges.length ? (
                <div className="gauge-row">
                  {gauges.map((g) => (
                    <Gauge key={g.label} label={g.label} raw={g.raw} percent={g.percent} />
                  ))}
                </div>
              ) : (
                <p className="agri-card-empty">Aucune donnée de sol chiffrée dans le rapport.</p>
              )}
            </div>

            <div className="agri-card">
              <div className="agri-card-h">Image satellite (NDVI)</div>
              {ndviOverlay ? (
                <div className="agri-ndvi-preview">
                  <img src={`data:image/png;base64,${ndviOverlay.image_base64}`} alt="Carte NDVI de la parcelle" />
                </div>
              ) : (
                <div className="agri-ndvi-placeholder">
                  <button className="hmbtn" onClick={onRequestNdvi} disabled={ndviLoading}>
                    {ndviLoading ? "🛰️ Chargement…" : "🛰️ Afficher la carte NDVI"}
                  </button>
                </div>
              )}
            </div>

            <div className="agri-card">
              <div className="agri-card-h">Ce que ça veut dire</div>
              {vegSection?.body ? (
                <Prose text={vegSection.body} className="agri-insight" />
              ) : (
                <p className="agri-card-empty">Pas d'interprétation disponible pour cette parcelle.</p>
              )}
            </div>
          </div>

          <div className="agri-crops-head">
            <div>
              <h2>Top {cropRows.length || 5} cultures recommandées</h2>
              <p>Triées par score de compatibilité, calculé à partir du sol, du climat et du contexte parcellaire.</p>
            </div>
            <div className="agri-year-tag">Année {year}</div>
          </div>

          {cropRows.length ? (
            <div className="agri-crop-grid">
              {cropRows.map((row, i) => (
                <div className="agri-crop-card" key={row.name + i}>
                  <div className="agri-crop-top">
                    <div className={`crnk ${i === 0 ? "r1" : ""}`}>{i + 1}</div>
                    <div className="agri-crop-name">{row.name}</div>
                    <div className="agri-crop-score">{Math.round(row.score * 100)}%</div>
                  </div>
                  {row.reason && <Prose text={row.reason} className="agri-crop-reason" />}
                  {row.extra.length > 0 && (
                    <div className="agri-crop-stats">
                      {row.extra.map((val, j) => (
                        <span className="agri-crop-stat" key={j}>
                          {val}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="agri-card">
              <p className="agri-card-empty">Aucune culture recommandée n'a pu être extraite du rapport.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
