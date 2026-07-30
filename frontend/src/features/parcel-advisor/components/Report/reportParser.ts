export type SectionType = "summary" | "soil" | "weather" | "vegetation" | "crops" | "claims" | "generic";

export interface ParsedSection {
  type: SectionType;
  heading: string;
  body: string;
}

/**
 * Splits the Stage-2 markdown report on "## " / "### " / "#### " headings and
 * classifies each block by heading keywords so the UI can render a dedicated
 * card per topic (sol, météo, cultures, ...) instead of a wall of markdown.
 * Stays permissive (2-4 hashes) as a safety net for reports generated before
 * a consistent "## " heading convention was enforced server-side.
 */
export function parseSections(markdown: string): ParsedSection[] {
  if (!markdown) return [];
  const parts = markdown.split(/\n(?=#{2,4}\s)/g);
  const out: ParsedSection[] = [];

  parts.forEach((part) => {
    const lines = part.trim().split("\n");
    let heading = (lines[0] ?? "").replace(/^#+\s*/, "").replace(/\*\*/g, "").trim();
    let body = lines.slice(1).join("\n").trim();

    if (!heading && !body) return;
    if (!heading) {
      heading = "Résumé";
      body = part.trim();
    }

    const hl = heading.toLowerCase();
    let type: SectionType = "generic";
    if (/résumé|resume|parcelle/i.test(hl)) type = "summary";
    else if (/sol|pédol|pedol|texture|ph|matière|matiere|argile|limon|sable|azote/i.test(hl)) type = "soil";
    else if (/météo|meteo|température|temperature|précip|precip|climat|hydrique/i.test(hl)) type = "weather";
    else if (/végétation|vegetation|ndvi|satellite/i.test(hl)) type = "vegetation";
    else if (/culture|recommand|pertinence|score/i.test(hl)) type = "crops";
    else if (/pratique|bonne|conseil|source|fond/i.test(hl)) type = "claims";

    out.push({ type, heading, body });
  });

  return out;
}

export interface KeyValue {
  key: string;
  val: string;
  note?: string;
}

/** Extracts "- **Label**: value (note)" style bullet lines into structured key/value pairs. */
export function extractKeyValues(body: string): KeyValue[] {
  const kvs: KeyValue[] = [];
  const re = /[-*]\s*\*{0,2}([^:*\n]+)\*{0,2}\s*:\s*\*{0,2}([^(\n]{1,60})\*{0,2}(?:\s*[([]([^)\n)\]]{1,80})[)\]])?/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(body)) !== null) {
    const key = m[1].replace(/\*/g, "").trim();
    const val = m[2].replace(/\*/g, "").trim();
    const note = m[3]?.trim();
    if (key.length < 40 && val.length < 60) kvs.push({ key, val, note });
  }
  return kvs;
}

/** Strips extracted key/value bullet lines from a body, leaving free-form prose. */
export function stripKeyValueLines(body: string): string {
  return body
    .split("\n")
    .filter((line) => !/^[-*]\s*[^:]+:/.test(line) || line.trim().length <= 30)
    .join("\n")
    .trim();
}

export interface CropRow {
  name: string;
  score: number;
  reason: string;
  /** Any extra markdown-table columns beyond name/score/reason (e.g. rendement, valeur nette), in source order. */
  extra: string[];
}

/** Parses the "Cultures recommandées" section, either as a markdown table or as "### N. Nom" blocks. */
export function parseCropRows(body: string): CropRow[] {
  const rows: CropRow[] = [];

  body.split("\n").forEach((line) => {
    const cells = line.split("|").map((c) => c.trim()).filter(Boolean);
    if (cells.length >= 2 && !line.includes("---") && !/culture|score/i.test(line)) {
      rows.push({
        name: cells[0],
        score: parseFloat(cells[1]) || 0,
        reason: cells[2] || "",
        extra: cells.slice(3),
      });
    }
  });

  if (rows.length) return rows;

  const blocks = body.split(/\n(?=#{3}\s*\d)/g);
  blocks.forEach((block) => {
    const nameMatch = block.match(/#{3}\s*\d+\.\s*(.+)/);
    const scoreMatch = block.match(/Score\s*:\s*(\d+(?:[.,]\d+)?)\s*%/i);
    if (!nameMatch) return;
    const name = nameMatch[1].replace(/\*\*/g, "").trim();
    const score = scoreMatch ? parseFloat(scoreMatch[1].replace(",", ".")) / 100 : 0;
    const reason = block
      .replace(/#{3}\s*\d+\.\s*.+/, "")
      .replace(/\*\*Score\s*:.+?\*\*/i, "")
      .trim();
    rows.push({ name, score, reason, extra: [] });
  });

  return rows;
}

export interface SoilGauge {
  label: string;
  /** Raw text as reported by the backend (e.g. "6.4", "2.3%", "Bon") — never fabricated. */
  raw: string;
  /** Best-effort 0-100 fill for the gauge ring, derived from `raw`. */
  percent: number;
}

const GAUGE_DEFS: { label: string; match: RegExp; toPercent: (n: number, raw: string) => number }[] = [
  { label: "pH", match: /^ph$/i, toPercent: (n) => (n / 14) * 100 },
  {
    label: "Matière organique",
    match: /mati[eè]re organique|humus/i,
    toPercent: (n, raw) => (raw.includes("%") ? n : Math.min(n * 10, 100)),
  },
  { label: "Azote", match: /azote/i, toPercent: (n, raw) => (raw.includes("%") ? n : Math.min((n / 20) * 100, 100)) },
  { label: "Drainage", match: /drainage/i, toPercent: (n, raw) => (raw.includes("%") ? n : Math.min((n / 10) * 100, 100)) },
];

/**
 * Extracts up to four soil metrics (pH, matière organique, azote, drainage) from the
 * soil section's key/value bullets for the gauge cards. Only returns gauges for metrics
 * actually present in the report — never invents a value the backend didn't provide.
 */
export function extractSoilGauges(body: string): SoilGauge[] {
  const kvs = extractKeyValues(body);
  const gauges: SoilGauge[] = [];

  for (const def of GAUGE_DEFS) {
    const kv = kvs.find((k) => def.match.test(k.key));
    if (!kv) continue;
    const numMatch = kv.val.match(/-?\d+(?:[.,]\d+)?/);
    if (!numMatch) continue;
    const n = parseFloat(numMatch[0].replace(",", "."));
    if (Number.isNaN(n)) continue;
    const percent = Math.max(0, Math.min(100, def.toPercent(n, kv.val)));
    gauges.push({ label: def.label, raw: kv.val, percent });
  }

  return gauges;
}
