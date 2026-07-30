import { CropRecommendations } from "./CropRecommendations";
import { KeyValueGrid } from "./KeyValueGrid";
import { Prose } from "./Prose";
import { Section } from "./Section";
import type { ParsedSection } from "./reportParser";
import { stripKeyValueLines } from "./reportParser";

function BodyWithKeyValues({ body }: { body: string }) {
  const remainder = stripKeyValueLines(body);
  return (
    <>
      <KeyValueGrid body={body} />
      {remainder && <Prose text={remainder} />}
    </>
  );
}

export function ReportSection({ section }: { section: ParsedSection }) {
  switch (section.type) {
    case "summary":
      return (
        <Section icon="📐" iconClass="ico-n" title={section.heading} subtitle="Informations générales sur la parcelle">
          <BodyWithKeyValues body={section.body} />
        </Section>
      );
    case "soil":
      return (
        <Section icon="🌍" iconClass="ico-s" title={section.heading} subtitle="Analyse physico-chimique du sol">
          <BodyWithKeyValues body={section.body} />
        </Section>
      );
    case "weather":
      return (
        <Section icon="⛅" iconClass="ico-w" title={section.heading} subtitle="Données météorologiques récentes">
          <BodyWithKeyValues body={section.body} />
        </Section>
      );
    case "vegetation":
      return (
        <Section icon="🛰️" iconClass="ico-v" title={section.heading} subtitle="Indice de végétation (NDVI) par satellite">
          <BodyWithKeyValues body={section.body} />
        </Section>
      );
    case "crops":
      return (
        <Section icon="🌿" iconClass="ico-c" title={section.heading} subtitle="Classées par score de pertinence (0–100 %)">
          <CropRecommendations body={section.body} />
        </Section>
      );
    case "claims": {
      const bullets = section.body
        .split("\n")
        .map((line) => line.replace(/^[-*•]\s*/, "").trim())
        .filter((line) => line.length > 8);
      return (
        <Section icon="📚" iconClass="ico-n" title={section.heading} subtitle="Recommandations fondées sur des sources scientifiques">
          {bullets.length ? (
            bullets.map((bullet, i) => (
              <div className="sclaim" key={i}>
                <Prose text={bullet} className="sclaim-prose" />
              </div>
            ))
          ) : (
            <Prose text={section.body} />
          )}
        </Section>
      );
    }
    default:
      return (
        <Section icon="📋" iconClass="ico-n" title={section.heading}>
          <Prose text={section.body} />
        </Section>
      );
  }
}

export function WarningsSection({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <Section icon="🔔" iconClass="ico-x" title="Avertissements" subtitle="Données manquantes ou lacunes identifiées" warn>
      {warnings.map((w, i) => (
        <div className="witem" key={i}>
          <span>⚠️</span>
          <span>{w}</span>
        </div>
      ))}
    </Section>
  );
}

export function UnverifiedFiguresSection({ figures }: { figures: string[] }) {
  if (!figures.length) return null;
  return (
    <Section
      icon="🚩"
      iconClass="ico-x"
      title="Chiffres non vérifiés"
      subtitle="Ces valeurs apparaissent sans correspondre aux données sources — à vérifier manuellement"
      warn
    >
      {figures.map((figure, i) => (
        <div className="witem" key={i}>
          <span>🚩</span>
          <span>{figure}</span>
        </div>
      ))}
    </Section>
  );
}
