interface ActionButtonsProps {
  parcelSelected: boolean;
  ndviAvailable: boolean;
  ndviActive: boolean;
  ndviLoading: boolean;
  adviseLoading: boolean;
  onToggleNdvi: () => void;
  onAdvise: () => void;
}

export function ActionButtons({
  parcelSelected,
  ndviAvailable,
  ndviActive,
  ndviLoading,
  adviseLoading,
  onToggleNdvi,
  onAdvise,
}: ActionButtonsProps) {
  if (!parcelSelected) return null;

  return (
    <>
      {ndviAvailable && (
        <button
          className={`hmbtn${ndviActive ? " on" : ""}`}
          onClick={onToggleNdvi}
          disabled={ndviLoading}
        >
          {ndviLoading
            ? "🛰️ Chargement…"
            : ndviActive
              ? "🛰️ Masquer la carte NDVI"
              : "🛰️ Afficher la carte NDVI"}
        </button>
      )}

      <button className="abtn" onClick={onAdvise} disabled={adviseLoading}>
        {adviseLoading ? "⏳ Analyse en cours…" : "🔍 Obtenir les recommandations"}
      </button>
    </>
  );
}
