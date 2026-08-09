/**
 * Suivi des dépenses réelles saisies depuis Aujourd'hui.
 * Clé par décision Business pour que le graphique "réel vs prévu"
 * reste cohérent avec le scénario confirmé.
 */

export type SpendEntry = {
  id: string;
  amount: number;
  date: string; // YYYY-MM-DD
  label: string;
  createdAt: string;
};

const STORAGE_KEY = "agriguide.monitoring.spend_entries";

type Store = Record<string, SpendEntry[]>;

function readStore(): Store {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Store;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(store: Store) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // ignore (mode privé, quota...)
  }
}

export function loadSpendEntries(decisionId: string): SpendEntry[] {
  const entries = readStore()[decisionId] ?? [];
  return [...entries].sort((a, b) => b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt));
}

export function addSpendEntry(
  decisionId: string,
  input: { amount: number; date: string; label?: string },
): SpendEntry[] {
  const entry: SpendEntry = {
    id: crypto.randomUUID(),
    amount: Math.round(input.amount * 100) / 100,
    date: input.date,
    label: (input.label ?? "").trim() || "Dépense",
    createdAt: new Date().toISOString(),
  };
  const store = readStore();
  const next = [entry, ...(store[decisionId] ?? [])];
  store[decisionId] = next;
  writeStore(store);
  return loadSpendEntries(decisionId);
}

export function removeSpendEntry(decisionId: string, entryId: string): SpendEntry[] {
  const store = readStore();
  store[decisionId] = (store[decisionId] ?? []).filter((e) => e.id !== entryId);
  writeStore(store);
  return loadSpendEntries(decisionId);
}

export function monthKey(dateIso: string): string {
  return dateIso.slice(0, 7); // YYYY-MM
}

export function monthLabelFr(yyyyMm: string): string {
  const [y, m] = yyyyMm.split("-").map(Number);
  const label = new Intl.DateTimeFormat("fr-FR", { month: "short" }).format(new Date(y, m - 1, 1));
  return label.replace(/\.$/, "").replace(/^./, (c) => c.toUpperCase());
}
