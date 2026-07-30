import { useEffect } from "react";
import type { AdvisorReport } from "../../types/api";
import { Prose } from "./Prose";
import { parseSections } from "./reportParser";
import { ReportSection, UnverifiedFiguresSection, WarningsSection } from "./ReportSections";
import "./ReportModal.css";

interface ReportModalProps {
  report: AdvisorReport | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export function ReportModal({ report, loading, error, onClose }: ReportModalProps) {
  const open = loading || error !== null || report !== null;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const title = report?.parcel_id ? `Rapport — Réf. ${report.parcel_id}` : "Rapport agronomique";
  const subtitle = loading
    ? undefined
    : `Généré le ${new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}`;

  const sections = report ? parseSections(report.report_markdown) : [];

  return (
    <div className="report-overlay" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="report-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="report-head">
          <div className="bicon">🌾</div>
          <div className="report-head-text">
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button className="report-close" onClick={onClose} aria-label="Fermer le rapport">
            ✕
          </button>
        </div>

        <div className="report-body">
          {loading && (
            <div className="lstate">
              <div className="spin" />
              <p>
                Analyse en cours — génération du rapport…
                <br />
                Cela peut prendre quelques secondes.
              </p>
            </div>
          )}

          {error && (
            <div className="rsec rsec-warn">
              <div className="rsh">
                <div className="sico ico-x">❌</div>
                <div className="stit">Erreur</div>
              </div>
              <Prose text={error} />
            </div>
          )}

          {report && (
            <>
              {sections.length ? (
                sections.map((section, i) => <ReportSection section={section} key={i} />)
              ) : (
                <div className="rsec">
                  <Prose text={report.report_markdown} />
                </div>
              )}
              <WarningsSection warnings={report.warnings} />
              <UnverifiedFiguresSection figures={report.unverified_figures} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
