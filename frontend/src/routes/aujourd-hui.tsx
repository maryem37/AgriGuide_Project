import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { useCountUp } from "@/components/motion/useCountUp";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import type { LatLng, TerrainOut } from "@/lib/authApi";
import { cultureLabel, loadRealCropRecommendations } from "@/lib/cropRecommendations";
import { equipementLabel } from "@/lib/equipements";
import { loadFarmerDecision } from "@/lib/farmerDecision";
import { fetchLatestFarmerDecision, type FarmerDecisionResponse } from "@/lib/businessApi";
import {
  addSpendEntry,
  loadSpendEntries,
  monthKey,
  monthLabelFr,
  removeSpendEntry,
  type SpendEntry,
} from "@/lib/spendTracking";
import {
  analyzeMonitoringDay,
  MonitoringApiError,
  type AnalyzeResponse,
  type CropAlert,
} from "@/lib/monitoringApi";
import {
  AlertTriangle,
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  Cloud,
  CloudSun,
  Droplets,
  LineChart,
  Loader2,
  Plus,
  RefreshCw,
  Sprout,
  Trash2,
  Wallet,
  Wind,
  Recycle,
} from "lucide-react";

export const Route = createFileRoute("/aujourd-hui")({
  head: () => ({
    meta: [
      { title: "Aujourd'hui - AgriMent" },
      {
        name: "description",
        content:
          "Briefing du jour : allocation des cultures, météo, irrigation, alertes et tâches.",
      },
      { property: "og:title", content: "Aujourd'hui - AgriMent" },
      {
        property: "og:description",
        content: "Votre journée de terrain en un coup d'œil.",
      },
    ],
  }),
  component: Page,
});

const CROP_IMAGES: Record<string, string> = {
  tomate: "/img/marketplace/tomate.jpg",
  pomme_de_terre: "/img/marketplace/pomme-de-terre.jpg",
  ble: "/img/marketplace/ble.jpg",
  ble_tendre: "/img/marketplace/ble.jpg",
  colza: "/img/marketplace/colza.jpg",
  tournesol: "/img/marketplace/tournesol.jpg",
  mais: "/img/marketplace/tournesol.jpg",
  orge: "/img/marketplace/ble.jpg",
};

function normalizeCropKey(culture: string): string {
  return culture
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function cropImage(culture: string): string {
  const key = normalizeCropKey(culture);
  return CROP_IMAGES[key] ?? CROP_IMAGES[culture] ?? "/img/marketplace/ble.jpg";
}

function terrainCentroid(points: LatLng[]): { lat: number; lon: number } | null {
  if (!points.length) return null;
  const lat = points.reduce((s, p) => s + p[0], 0) / points.length;
  const lon = points.reduce((s, p) => s + p[1], 0) / points.length;
  return { lat, lon };
}

function mapWaterSensitivity(niveau: unknown): string | undefined {
  if (typeof niveau !== "string") return undefined;
  const n = niveau.toLowerCase();
  if (n === "eleve" || n === "élevé" || n === "high") return "high";
  if (n === "modere" || n === "modéré" || n === "moderate") return "moderate";
  if (n === "faible" || n === "low") return "low";
  return undefined;
}

function formatEuro(n: number) {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatDayLabel(d = new Date()) {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(d);
}

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function campaignMonthKeys(decision: FarmerDecisionResponse): string[] {
  let start = new Date(decision.created_at);
  if (Number.isNaN(start.getTime())) {
    const now = new Date();
    start = new Date(now.getFullYear(), now.getMonth() - 2, 1);
  }
  const maturityTimes = decision.allocations
    .map((a) => (a.date_maturite_prevue ? new Date(a.date_maturite_prevue).getTime() : NaN))
    .filter((t) => Number.isFinite(t));
  const end = maturityTimes.length
    ? new Date(Math.max(...maturityTimes))
    : new Date(start.getFullYear(), start.getMonth() + 4, 1);
  const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
  const last = new Date(end.getFullYear(), end.getMonth(), 1);
  const keys: string[] = [];
  while (cursor <= last && keys.length < 8) {
    keys.push(
      `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}`,
    );
    cursor.setMonth(cursor.getMonth() + 1);
  }
  return keys.length ? keys : [monthKey(todayIso())];
}

const costChartConfig = {
  prevu: { label: "prévu", color: "var(--chart-2)" },
  reel: { label: "réel", color: "var(--chart-1)" },
} satisfies ChartConfig;

function AllocationSummaryCard({
  totalHa,
  culturesCount,
}: {
  totalHa: number;
  culturesCount: number;
}) {
  const [haRef, haDisplayed] = useCountUp<HTMLParagraphElement>(totalHa, {
    duration: 1400,
    decimals: 1,
  });
  const [culturesRef, culturesDisplayed] = useCountUp<HTMLParagraphElement>(culturesCount, {
    duration: 1400,
    decimals: 0,
  });

  return (
    <Reveal delay={60} className="h-full">
      <div className="flex h-full flex-col overflow-hidden rounded-3xl bg-card p-5 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.4)] ring-1 ring-border/80 md:p-6">
        <h2 className="font-display text-xl font-semibold tracking-tight text-primary">
          Suivi de campagne
        </h2>
        <div className="mt-5 flex flex-1 flex-col justify-center gap-5">
          <div className="flex items-start gap-3">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">Surface allouée</p>
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Sprout className="h-4 w-4" />
                </span>
              </div>
              <p
                ref={haRef}
                className="mt-1 font-display text-3xl font-semibold tracking-tight text-primary tabular-nums"
              >
                {haDisplayed.toFixed(1)} ha
              </p>
            </div>
          </div>
          <div className="h-px bg-border/70" />
          <div className="flex items-start gap-3">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">Cultures actives</p>
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <LineChart className="h-4 w-4" />
                </span>
              </div>
              <p
                ref={culturesRef}
                className="mt-1 font-display text-3xl font-semibold tracking-tight text-primary tabular-nums"
              >
                {Math.round(culturesDisplayed)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

function CostVsPlannedChart({
  decision,
  spends,
}: {
  decision: FarmerDecisionResponse;
  spends: SpendEntry[];
}) {
  const months = useMemo(() => campaignMonthKeys(decision), [decision]);
  const plannedPerMonth = decision.cout_final / months.length;
  const spentByMonth = useMemo(() => {
    const map = new Map<string, number>();
    for (const entry of spends) {
      const key = monthKey(entry.date);
      map.set(key, (map.get(key) ?? 0) + entry.amount);
    }
    return map;
  }, [spends]);

  const chartData = months.map((key) => ({
    mois: monthLabelFr(key),
    prevu: Math.round(plannedPerMonth),
    reel: Math.round(spentByMonth.get(key) ?? 0),
  }));

  return (
    <Reveal delay={120} className="h-full">
      <div className="flex h-full flex-col overflow-hidden rounded-3xl bg-card p-5 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.4)] ring-1 ring-border/80 md:p-6">
        <div className="flex items-center gap-2.5">
          <Wallet className="h-4 w-4 text-primary" />
          <h2 className="font-display text-xl font-semibold tracking-tight text-primary">
            Coût réel vs. prévu
          </h2>
        </div>

        <ChartContainer config={costChartConfig} className="mt-3 aspect-[5/3] w-full min-h-0 flex-1">
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -8, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="4 4" />
            <XAxis dataKey="mois" tickLine={false} axisLine={false} tickMargin={6} fontSize={11} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={36}
              fontSize={11}
              tickFormatter={(v) => String(Math.round(Number(v)))}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value, name) => (
                    <span className="font-medium">
                      {formatEuro(Number(value))}{" "}
                      <span className="text-muted-foreground">
                        {name === "prevu" ? "prévu" : "réel"}
                      </span>
                    </span>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent className="pt-1" />} />
            <Bar dataKey="prevu" fill="var(--color-prevu)" radius={[4, 4, 0, 0]} maxBarSize={18} />
            <Bar dataKey="reel" fill="var(--color-reel)" radius={[4, 4, 0, 0]} maxBarSize={18} />
          </BarChart>
        </ChartContainer>
      </div>
    </Reveal>
  );
}

function SpendInputCard({
  spends,
  onAddSpend,
  onRemoveSpend,
}: {
  spends: SpendEntry[];
  onAddSpend: (input: { amount: number; date: string; label: string }) => void;
  onRemoveSpend: (id: string) => void;
}) {
  const [amountText, setAmountText] = useState("");
  const [labelText, setLabelText] = useState("");
  const [dateText, setDateText] = useState(todayIso);
  const [formError, setFormError] = useState<string | null>(null);

  function submitSpend(e: FormEvent) {
    e.preventDefault();
    const amount = Number(amountText.replace(",", ".").replace(/\s/g, ""));
    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError("Indiquez un montant valide en euros.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateText)) {
      setFormError("Indiquez une date valide.");
      return;
    }
    setFormError(null);
    onAddSpend({ amount, date: dateText, label: labelText });
    setAmountText("");
    setLabelText("");
    setDateText(todayIso());
  }

  return (
    <Reveal delay={180} className="mt-4">
      <div className="overflow-hidden rounded-3xl bg-card p-4 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.4)] ring-1 ring-border/80 md:p-5">
        <p className="text-sm font-medium text-primary">Saisir une dépense réelle</p>
        <form onSubmit={submitSpend} className="mt-3 grid gap-3 sm:grid-cols-[1fr_1.2fr_auto_auto]">
          <div className="relative">
            <Input
              type="text"
              inputMode="decimal"
              value={amountText}
              onChange={(e) => {
                setAmountText(e.target.value);
                setFormError(null);
              }}
              placeholder="Montant"
              aria-label="Montant dépensé"
              className="h-10 rounded-xl pr-8"
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
              €
            </span>
          </div>
          <Input
            type="text"
            value={labelText}
            onChange={(e) => setLabelText(e.target.value)}
            placeholder="Libellé (engrais, irrigation…)"
            aria-label="Libellé de la dépense"
            className="h-10 rounded-xl"
          />
          <Input
            type="date"
            value={dateText}
            onChange={(e) => setDateText(e.target.value)}
            aria-label="Date de la dépense"
            className="h-10 rounded-xl"
          />
          <Button type="submit" className="h-10 rounded-xl">
            <Plus className="mr-1.5 h-4 w-4" />
            Ajouter
          </Button>
        </form>
        {formError && <p className="mt-2 text-xs text-destructive">{formError}</p>}

        {spends.length > 0 && (
          <ul className="mt-3 max-h-28 space-y-1.5 overflow-y-auto">
            {spends.slice(0, 6).map((entry) => (
              <li
                key={entry.id}
                className="flex items-center justify-between gap-3 rounded-xl bg-muted/40 px-3 py-1.5 text-sm"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{entry.label}</div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(entry.date).toLocaleDateString("fr-FR")}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="font-display font-semibold">{formatEuro(entry.amount)}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveSpend(entry.id)}
                    className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                    aria-label="Supprimer la dépense"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Reveal>
  );
}

function HectareBar({ ratio }: { ratio: number }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);
  return (
    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-primary/10">
      <div
        className="h-full rounded-full bg-gradient-to-r from-primary to-harvest transition-[width] duration-1000 ease-out"
        style={{ width: ready ? `${Math.round(Math.min(ratio, 1) * 100)}%` : "0%" }}
      />
    </div>
  );
}

function riskLabel(risk: string) {
  if (risk === "high") return "Élevé";
  if (risk === "medium") return "Moyen";
  return "Faible";
}

function Page() {
  const { user, token } = useAuth();
  const terrain: TerrainOut | undefined = user?.terrains[0];
  const localDecision = useMemo(
    () => (terrain ? loadFarmerDecision(terrain.id) : null),
    [terrain],
  );
  const persistedDecision = useQuery({
    queryKey: ["business-decision", terrain?.id],
    queryFn: async () => {
      try {
        if (!token) return localDecision;
        return await fetchLatestFarmerDecision(terrain!.id, token);
      } catch {
        return localDecision;
      }
    },
    enabled: Boolean(terrain),
  });
  const decision = persistedDecision.data ?? localDecision;
  const cropRecs = useMemo(
    () => (terrain ? loadRealCropRecommendations(terrain.id) : null),
    [terrain],
  );

  const [briefing, setBriefing] = useState<AnalyzeResponse | null>(null);
  const [done, setDone] = useState<Record<number, boolean>>({});
  const [spends, setSpends] = useState<SpendEntry[]>([]);

  useEffect(() => {
    if (!decision?.decision_id) {
      setSpends([]);
      return;
    }
    setSpends(loadSpendEntries(decision.decision_id));
  }, [decision?.decision_id]);

  const analyzeMutation = useMutation({
    mutationFn: analyzeMonitoringDay,
    onSuccess: (data) => {
      setBriefing(data);
      setDone({});
    },
  });

  const totalHa = decision?.superficie_totale_allouee_ha ?? 0;
  const allocations = decision?.allocations ?? [];

  useEffect(() => {
    if (!user || !terrain || !decision) return;
    const centroid = terrainCentroid(terrain.points);
    if (!centroid) return;

    const waterByCrop = new Map(
      (cropRecs ?? []).map((c) => [
        c.culture,
        mapWaterSensitivity(c.besoins_irrigation?.niveau),
      ]),
    );

    analyzeMutation.mutate({
      farmer_name: user.nom,
      terrain_id: terrain.id,
      location: {
        latitude: centroid.lat,
        longitude: centroid.lon,
        label: terrain.region ?? terrain.nom ?? undefined,
      },
      crops: decision.allocations.map((a) => ({
        crop_name: a.culture,
        hectares: a.hectares_alloues,
        water_sensitivity: waterByCrop.get(a.culture) ?? undefined,
      })),
      hardware_inventory: (user.equipements ?? []).map(equipementLabel),
    });
    // Intentionnel : une fois par terrain/décision au montage
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, terrain?.id, decision?.decision_id]);

  const tasks = briefing?.analysis.tasks ?? [];
  const cropAlerts: CropAlert[] = briefing?.analysis.crop_alerts ?? [];
  const weather = briefing?.weather_summary;
  const doneCount = Object.values(done).filter(Boolean).length;
  const dayLabel = formatDayLabel();

  if (!user) {
    return (
      <AppShell>
        <PageHeader icon={CalendarDays} title="Aujourd'hui" subtitle="Connexion requise" />
      </AppShell>
    );
  }

  if (!terrain) {
    return (
      <AppShell>
        <PageHeader icon={CalendarDays} title="Aujourd'hui" subtitle={dayLabel} />
        <div className="mt-6">
          <AlertBanner
            tone="info"
            title="Aucun terrain déclaré"
            action={
              <Button asChild size="sm" variant="outline">
                <Link to="/profil">Profil</Link>
              </Button>
            }
          >
            Ajoutez un terrain dans votre profil pour lancer le briefing quotidien.
          </AlertBanner>
        </div>
      </AppShell>
    );
  }

  if (!decision) {
    return (
      <AppShell>
        <PageHeader icon={CalendarDays} title="Aujourd'hui" subtitle={dayLabel} />
        <div className="mt-6">
          <AlertBanner
            tone="info"
            title="Aucune culture confirmée"
            action={
              <Button asChild size="sm" variant="outline">
                <Link to="/business">Financier</Link>
              </Button>
            }
          >
            Confirmez un scénario dans le conseiller Financier pour activer le suivi
            quotidien (météo, irrigation, tâches).
          </AlertBanner>
        </div>
      </AppShell>
    );
  }

  const toggle = (i: number) => setDone((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <AppShell>
      <PageHeader
        icon={CalendarDays}
        title="Aujourd'hui"
        subtitle={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span className="capitalize">{dayLabel}</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              <span className="weather-live-dot !bg-primary" />
              Briefing du matin
            </span>
          </span>
        }
      />

      <div className="mt-4 flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={analyzeMutation.isPending}
          onClick={() => {
            const centroid = terrainCentroid(terrain.points);
            if (!centroid) return;
            analyzeMutation.mutate({
              farmer_name: user.nom,
              terrain_id: terrain.id,
              location: {
                latitude: centroid.lat,
                longitude: centroid.lon,
                label: terrain.region ?? terrain.nom ?? undefined,
              },
              crops: decision.allocations.map((a) => ({
                crop_name: a.culture,
                hectares: a.hectares_alloues,
              })),
              hardware_inventory: (user.equipements ?? []).map(equipementLabel),
            });
          }}
        >
          {analyzeMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Actualiser
        </Button>
      </div>

      {analyzeMutation.isError && (
        <div className="mt-4">
          <AlertBanner tone="danger" title="Briefing indisponible">
            {analyzeMutation.error instanceof MonitoringApiError
              ? analyzeMutation.error.message
              : "Une erreur est survenue."}
          </AlertBanner>
        </div>
      )}

      <div className="mt-6 grid gap-4 md:grid-cols-2 md:items-stretch">
        <AllocationSummaryCard totalHa={totalHa} culturesCount={allocations.length} />
        <CostVsPlannedChart decision={decision} spends={spends} />
      </div>
      <SpendInputCard
        spends={spends}
        onAddSpend={(input) => {
          setSpends(addSpendEntry(decision.decision_id, input));
        }}
        onRemoveSpend={(id) => {
          setSpends(removeSpendEntry(decision.decision_id, id));
        }}
      />

      <Reveal delay={120} className="mt-6">
        <div className="overflow-hidden rounded-3xl bg-card p-5 md:p-6 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.4)] ring-1 ring-border/80">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Sprout className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-display text-xl font-semibold tracking-tight">
                  Allocation des cultures
                </h2>
                <p className="text-sm text-muted-foreground">
                  {totalHa.toFixed(1)} ha répartis sur {allocations.length} culture
                  {allocations.length > 1 ? "s" : ""}
                  {terrain.nom ? ` · ${terrain.nom}` : ""}
                </p>
              </div>
            </div>
            {totalHa > 0 && (
              <div className="flex h-3 w-full max-w-[12rem] overflow-hidden rounded-full sm:w-48">
                {allocations.map((a) => (
                  <span
                    key={`${a.scenario_id}-${a.culture}`}
                    className="h-full first:rounded-l-full last:rounded-r-full"
                    style={{
                      width: `${(a.hectares_alloues / totalHa) * 100}%`,
                      backgroundImage: `url(${cropImage(a.culture)})`,
                      backgroundSize: "cover",
                      backgroundPosition: "center",
                    }}
                    title={`${cultureLabel(a.culture)} ${a.hectares_alloues} ha`}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="mt-6 space-y-4">
            {allocations.map((a, i) => (
              <Reveal key={`${a.scenario_id}-${a.culture}`} from="left" delay={160 + i * 100}>
                <div className="group flex items-center gap-3 md:gap-4">
                  <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl ring-1 ring-border/70 shadow-sm transition duration-500 group-hover:scale-105 group-hover:rotate-1 md:h-14 md:w-14">
                    <img
                      src={cropImage(a.culture)}
                      alt={cultureLabel(a.culture)}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <span className="font-semibold">{cultureLabel(a.culture)}</span>
                      <span className="text-sm font-medium tabular-nums text-muted-foreground">
                        {a.hectares_alloues} ha
                      </span>
                    </div>
                    <HectareBar ratio={a.hectares_alloues / Math.max(totalHa, 0.01)} />
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Reveal>

      {allocations[0] && (
        <Reveal delay={160} className="mt-6">
          <Link
            to="/marketplace/nouveau"
            search={{ kind: "dechet", culture: allocations[0].culture }}
            className="group flex items-start gap-4 rounded-3xl border border-waste/30 bg-waste/10 p-5 transition hover:bg-waste/15"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-card text-waste-foreground">
              <Recycle className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="font-display text-lg font-semibold">
                Valorisez les déchets de {cultureLabel(allocations[0].culture)}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Après la récolte (prévue le{" "}
                {new Date(allocations[0].date_maturite_prevue).toLocaleDateString("fr-FR")}
                ), déposez paille, balles et autres résidus sur la marketplace.
              </p>
            </div>
          </Link>
        </Reveal>
      )}

      <Reveal delay={80} className="mt-6" threshold={0.05}>
        <div className="relative overflow-hidden rounded-3xl bg-[#E8F2E9] p-5 md:p-6 ring-1 ring-primary/10">
          <div
            className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-primary/10 blur-3xl"
            aria-hidden
          />
          <div className="relative flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#E8D5B0]/70 text-[#8B6914]">
                <Bell className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-display text-xl font-semibold tracking-tight text-primary">
                  Briefing agriculteur
                </h2>
                <p className="text-sm font-medium capitalize text-primary/70">{dayLabel}</p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sky/40 px-3 py-1 text-xs font-semibold text-sky-foreground">
              <Bell className="h-3.5 w-3.5" />
              Quotidien
            </span>
          </div>

          {analyzeMutation.isPending && !briefing ? (
            <div className="relative mt-5 space-y-3">
              <Skeleton className="h-28 w-full rounded-2xl" />
              <Skeleton className="h-20 w-full rounded-2xl" />
            </div>
          ) : (
            <>
              {briefing?.analysis.has_alert && briefing.analysis.alert_message && (
                <div className="relative mt-5">
                  <AlertBanner tone="warning" title="Alerte météo">
                    {briefing.analysis.alert_message}
                  </AlertBanner>
                </div>
              )}

              <div className="relative mt-5 rounded-2xl bg-[#D7E8D9]/80 p-4 ring-1 ring-primary/10">
                <div className="mb-3 flex items-center gap-2 font-semibold text-primary">
                  <CloudSun className="h-4 w-4 text-waste" />
                  Météo du jour
                  {weather?.location_label ? (
                    <span className="text-sm font-medium text-primary/60">
                      · {weather.location_label}
                    </span>
                  ) : null}
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    {
                      icon: CloudSun,
                      label:
                        weather?.today_max_temp_c != null && weather?.today_min_temp_c != null
                          ? `${Math.round(weather.today_max_temp_c)}° / ${Math.round(weather.today_min_temp_c)}°`
                          : "—",
                      hint: "Max / min",
                    },
                    {
                      icon: Cloud,
                      label: weather?.conditions_label ?? weather?.note ?? "—",
                      hint: "Conditions",
                    },
                    {
                      icon: Droplets,
                      label:
                        weather?.precipitation_sum_mm != null
                          ? `${weather.precipitation_sum_mm} mm`
                          : "—",
                      hint: "Précipitations",
                    },
                    {
                      icon: Wind,
                      label:
                        weather?.max_wind_speed_kmh != null
                          ? `${Math.round(weather.max_wind_speed_kmh)} km/h`
                          : "—",
                      hint: "Vent",
                    },
                  ].map(({ icon: Icon, label, hint }) => (
                    <div
                      key={hint}
                      className="flex items-start gap-2.5 rounded-xl bg-white/55 px-3 py-2.5 backdrop-blur-sm transition hover:-translate-y-0.5"
                    >
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <div className="min-w-0">
                        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          {hint}
                        </p>
                        <p className="text-sm font-semibold leading-snug text-foreground">
                          {label}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="relative mt-3 flex gap-3 rounded-2xl bg-sky/25 p-4 ring-1 ring-sky/40">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky/50 text-sky-foreground">
                  <Droplets className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="font-semibold text-primary">Gestion de l&apos;irrigation</h3>
                  <p className="mt-1 text-sm leading-relaxed text-foreground/80">
                    {briefing?.analysis.daily_advice ??
                      "Le briefing arrive…"}
                  </p>
                  {briefing?.analysis.water_saving_technique ? (
                    <p className="mt-2 text-sm leading-relaxed text-primary/80">
                      {briefing.analysis.water_saving_technique}
                    </p>
                  ) : null}
                </div>
              </div>
            </>
          )}
        </div>
      </Reveal>

      {cropAlerts.length > 0 && (
        <div className="mt-8">
          <Reveal className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-waste" />
            <h2 className="font-display text-xl font-semibold tracking-tight">
              Vigilance cultures
            </h2>
          </Reveal>
          <div className="grid gap-3">
            {cropAlerts.map((alert, i) => (
              <Reveal key={`${alert.crop}-${i}`} from="up" delay={i * 100}>
                <div className="group flex flex-col gap-3 rounded-2xl bg-card p-3.5 ring-1 ring-border/80 transition-all duration-400 hover:-translate-y-0.5 hover:shadow-lift sm:flex-row sm:items-center sm:gap-4 sm:p-4">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl ring-1 ring-border/60 transition duration-500 group-hover:scale-105">
                      <img
                        src={cropImage(alert.crop)}
                        alt=""
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">{cultureLabel(alert.crop)}</span>
                        <span
                          className={cn(
                            "rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide",
                            alert.risk === "high"
                              ? "bg-destructive/15 text-destructive"
                              : alert.risk === "medium"
                                ? "bg-waste/25 text-waste-foreground"
                                : "bg-harvest/20 text-harvest",
                          )}
                        >
                          {riskLabel(alert.risk)}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-sm text-muted-foreground">
                        {alert.message}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm font-medium text-primary sm:max-w-[16rem] sm:text-right">
                    → {alert.action}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      )}

      {tasks.length > 0 && (
        <Reveal delay={100} className="mt-8">
          <div className="overflow-hidden rounded-3xl bg-card p-5 md:p-6 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.35)] ring-1 ring-border/80">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <CheckCircle2 className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="font-display text-xl font-semibold tracking-tight">
                    Plan du jour
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {doneCount}/{tasks.length} terminée{doneCount > 1 ? "s" : ""}
                  </p>
                </div>
              </div>
              <div className="h-2 w-28 overflow-hidden rounded-full bg-primary/10 sm:w-36">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
                  style={{
                    width: `${tasks.length ? (doneCount / tasks.length) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            <ul className="mt-5 space-y-2">
              {tasks.map((task, i) => {
                const checked = Boolean(done[i]);
                return (
                  <li key={`${task}-${i}`}>
                    <button
                      type="button"
                      onClick={() => toggle(i)}
                      className={cn(
                        "press flex w-full items-start gap-3 rounded-2xl border px-3.5 py-3 text-left transition-all duration-300",
                        checked
                          ? "border-primary/25 bg-primary/5"
                          : "border-border/80 bg-background/60 hover:border-primary/30 hover:bg-secondary/40",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-300",
                          checked
                            ? "scale-100 border-primary bg-primary text-primary-foreground"
                            : "border-muted-foreground/35 bg-card",
                        )}
                      >
                        {checked && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
                      </span>
                      <span
                        className={cn(
                          "text-sm leading-snug transition-colors",
                          checked
                            ? "text-muted-foreground line-through"
                            : "text-foreground",
                        )}
                      >
                        {task}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </Reveal>
      )}
    </AppShell>
  );
}
