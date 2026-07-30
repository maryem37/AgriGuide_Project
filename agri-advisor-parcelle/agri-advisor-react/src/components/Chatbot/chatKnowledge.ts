import type { NeighborCropContext, ParcelResolution } from "../../types/api";
import { extractSoilGauges, parseCropRows, parseSections } from "../Report/reportParser";

export interface ChatContext {
  parcel: ParcelResolution | null;
  neighbors: NeighborCropContext | null;
  reportMarkdown: string | null;
  ndviAvailable: boolean;
}

const NO_PARCEL = "Sélectionnez d'abord une parcelle sur la carte (onglet Agriculture ou Carte) et je pourrai vous répondre précisément 🗺️";
const NO_REPORT = "Lancez d'abord « Obtenir les recommandations » sur votre parcelle, j'aurai alors ces informations sous la main 🔍";

function soilLine(reportMarkdown: string, label: string): string | null {
  const sections = parseSections(reportMarkdown);
  const soil = sections.find((s) => s.type === "soil");
  if (!soil) return null;
  const gauge = extractSoilGauges(soil.body).find((g) => g.label.toLowerCase() === label.toLowerCase());
  return gauge ? gauge.raw : null;
}

function topCrops(reportMarkdown: string) {
  const sections = parseSections(reportMarkdown);
  const crops = sections.find((s) => s.type === "crops");
  return crops ? parseCropRows(crops.body) : [];
}

interface Rule {
  test: RegExp;
  answer: (ctx: ChatContext) => string;
}

const RULES: Rule[] = [
  {
    test: /comment (utiliser|marche|fonctionne|[çc]a marche)/i,
    answer: () =>
      "C'est simple : cliquez sur une parcelle dans l'onglet Carte, puis « Obtenir les recommandations ». Je vous aide ensuite à interpréter le sol, le NDVI et les cultures conseillées.",
  },
  {
    test: /(comment )?s[ée]lectionner|choisir une parcelle/i,
    answer: () => "Allez dans l'onglet Carte et cliquez directement sur la parcelle qui vous intéresse — je la recherche au cadastre pour vous.",
  },
  {
    test: /bonjour|salut|coucou|hello/i,
    answer: () => "Bonjour ! Content de vous retrouver au champ 👋 Posez-moi une question sur votre parcelle.",
  },
  {
    test: /merci/i,
    answer: () => "Avec plaisir ! N'hésitez pas si vous avez d'autres questions sur la parcelle.",
  },
  {
    test: /(surface|hectare|taille|superficie)/i,
    answer: (ctx) => {
      if (!ctx.parcel) return NO_PARCEL;
      if (ctx.parcel.area_ha == null) return "Je n'ai pas de surface chiffrée pour cette parcelle, désolé.";
      return `Cette parcelle fait ${ctx.parcel.area_ha.toFixed(2)} ha, d'après le cadastre.`;
    },
  },
  {
    test: /(rpg|d[ée]clar[ée]e?|statut)/i,
    answer: (ctx) => {
      if (!ctx.parcel) return NO_PARCEL;
      if (ctx.parcel.is_agricultural === true) return "Bonne nouvelle : elle est déclarée comme terre agricole au RPG. ✅";
      if (ctx.parcel.is_agricultural === false) return "Elle n'apparaît pas comme déclarée au RPG — à vérifier auprès de la mairie ou de la DDT si besoin.";
      return "Je n'ai pas d'information de statut RPG certaine pour cette parcelle.";
    },
  },
  {
    test: /(culture actuelle|culture d[ée]clar[ée]e|qu['e]est[- ]ce qui (y )?pousse|actuellement cultiv)/i,
    answer: (ctx) => {
      if (!ctx.parcel) return NO_PARCEL;
      if (!ctx.parcel.crop_declared) return "Aucune culture déclarée n'est renseignée pour cette parcelle.";
      return `D'après le RPG, la culture actuellement déclarée est : ${ctx.parcel.crop_declared}.`;
    },
  },
  {
    test: /(voisin|alentour|autour)/i,
    answer: (ctx) => {
      if (!ctx.neighbors || !Object.keys(ctx.neighbors.crop_distribution_pct).length) {
        return ctx.parcel ? "Je n'ai pas encore de données sur les parcelles voisines." : NO_PARCEL;
      }
      const top = Object.entries(ctx.neighbors.crop_distribution_pct)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, pct]) => `${name} (${pct}%)`)
        .join(", ");
      return `Sur les ${ctx.neighbors.neighbor_count} parcelles voisines, les cultures les plus fréquentes sont : ${top}.`;
    },
  },
  {
    test: /\bph\b|acidit[ée]/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const val = soilLine(ctx.reportMarkdown, "pH");
      return val ? `Le pH du sol est de ${val}.` : "Le pH n'est pas renseigné dans le rapport pour cette parcelle.";
    },
  },
  {
    test: /mati[eè]re organique|humus/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const val = soilLine(ctx.reportMarkdown, "Matière organique");
      return val ? `Le taux de matière organique est de ${val}.` : "La matière organique n'est pas renseignée dans le rapport.";
    },
  },
  {
    test: /azote/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const val = soilLine(ctx.reportMarkdown, "Azote");
      return val ? `Le niveau d'azote relevé est : ${val}.` : "L'azote n'est pas renseigné dans le rapport.";
    },
  },
  {
    test: /drainage/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const val = soilLine(ctx.reportMarkdown, "Drainage");
      return val ? `Le drainage est estimé à : ${val}.` : "Le drainage n'est pas renseigné dans le rapport.";
    },
  },
  {
    test: /pourquoi|raison/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const rows = topCrops(ctx.reportMarkdown);
      if (!rows.length) return "Je n'ai pas de justification détaillée à vous donner pour l'instant.";
      const top = rows[0];
      return top.reason
        ? `Pour ${top.name} : ${top.reason.replace(/\*\*/g, "")}`
        : `${top.name} arrive en tête, mais le rapport ne détaille pas la raison précise.`;
    },
  },
  {
    test: /(recommand|meilleure culture|quelle culture|planter|semer)/i,
    answer: (ctx) => {
      if (!ctx.reportMarkdown) return NO_REPORT;
      const rows = topCrops(ctx.reportMarkdown);
      if (!rows.length) return "Je n'ai pas encore de cultures recommandées pour cette parcelle.";
      const names = rows.slice(0, 3).map((r) => r.name).join(", ");
      return `Ma meilleure piste est ${rows[0].name} (score ${Math.round(rows[0].score * 100)}%). Ensuite, je regarderais aussi : ${names}.`;
    },
  },
  {
    test: /ndvi|satellite|v[ée]g[ée]tation/i,
    answer: (ctx) => {
      if (!ctx.ndviAvailable) {
        return "La carte NDVI n'est pas encore affichée — cliquez sur « Afficher la carte NDVI » et je pourrai vous en parler.";
      }
      return "Le NDVI montre la vigueur de la végétation : plus c'est vert/foncé, plus la parcelle est en bonne santé végétale à cette date. Les zones plus claires ou rougeâtres méritent un coup d'œil au sol.";
    },
  },
];

const FALLBACK_SUGGESTIONS = [
  "Quelle est la surface de ma parcelle ?",
  "Quel est le statut RPG ?",
  "Quelles sont les cultures voisines ?",
];

export function answerQuestion(question: string, ctx: ChatContext): string {
  const rule = RULES.find((r) => r.test.test(question));
  if (rule) return rule.answer(ctx);
  return `Je ne suis pas sûr de bien comprendre. Essayez par exemple : « ${FALLBACK_SUGGESTIONS[0]} »`;
}

/** Suggested quick-reply chips, adapted to what data is currently available. */
export function getSuggestions(ctx: ChatContext): string[] {
  if (!ctx.parcel) {
    return ["Comment utiliser cette application ?", "Comment sélectionner une parcelle ?"];
  }
  if (!ctx.reportMarkdown) {
    return [
      "Quelle est la surface de ma parcelle ?",
      "Quel est le statut RPG ?",
      "Quelles sont les cultures voisines ?",
    ];
  }
  return [
    "Quelle culture recommandez-vous ?",
    "Pourquoi cette culture ?",
    "Quel est le pH du sol ?",
    "Que montre le NDVI ?",
  ];
}
