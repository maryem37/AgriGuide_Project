import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { useCountUp } from "@/components/motion/useCountUp";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import type { LatLng, TerrainOut } from "@/lib/authApi";
import { cultureLabel, loadRealCropRecommendations } from "@/lib/cropRecommendations";
import { equipementLabel } from "@/lib/equipements";
import { loadFarmerDecision } from "@/lib/farmerDecision";
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
  RefreshCw,
  Sprout,
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

function KpiCard({
  label,
  value,
  icon: Icon,
  accent,
  delay,
  format = "euro",
}: {
  label: string;
  value: number;
  icon: typeof Wallet;
  accent?: boolean;
  delay: number;
  format?: "euro" | "ha" | "int";
}) {
  const [ref, displayed] = useCountUp<HTMLParagraphElement>(value, {
    duration: 1400,
    decimals: format === "ha" ? 1 : 0,
  });
  const text =
    format === "euro"
      ? formatEuro(displayed)
      : format === "ha"
        ? `${displayed.toFixed(1)} ha`
        : String(Math.round(displayed));
  return (
    <Reveal from="up" delay={delay} className="flex">
      <div
        className={cn(
          "group relative flex flex-1 overflow-hidden rounded-3xl p-5 transition-all duration-400 hover:-translate-y-1",
          accent
            ? "bg-primary/10 ring-1 ring-primary/20 shadow-[0_12px_36px_-22px_rgba(47,82,48,0.45)]"
            : "bg-card ring-1 ring-border/80 shadow-[0_10px_30px_-20px_rgba(28,43,28,0.35)] hover:shadow-lift",
        )}
      >
        <div
          className={cn(
            "pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full blur-2xl transition-opacity duration-500",
            accent ? "bg-primary/25 opacity-80" : "bg-primary/10 opacity-0 group-hover:opacity-100",
          )}
          aria-hidden
        />
        <div className="relative flex w-full items-start justify-between gap-3">
          <div>
            <p className={cn("text-sm", accent ? "text-primary/80" : "text-muted-foreground")}>
              {label}
            </p>
            <p
              ref={ref}
              className="mt-2 font-display text-3xl font-semibold tracking-tight text-primary tabular-nums"
            >
              {text}
            </p>
          </div>
          <span
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-2xl transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3",
              accent ? "bg-primary/15 text-primary" : "bg-secondary text-primary",
            )}
          >
            <Icon className="h-5 w-5" />
          </span>
        </div>
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
  const { user } = useAuth();
  const terrain: TerrainOut | undefined = user?.terrains[0];
  const decision = useMemo(
    () => (terrain ? loadFarmerDecision(terrain.id) : null),
    [terrain],
  );
  const cropRecs = useMemo(
    () => (terrain ? loadRealCropRecommendations(terrain.id) : null),
    [terrain],
  );

  const [briefing, setBriefing] = useState<AnalyzeResponse | null>(null);
  const [done, setDone] = useState<Record<number, boolean>>({});

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
                <Link to="/business">Business</Link>
              </Button>
            }
          >
            Confirmez un scénario dans le conseiller Business pour activer le suivi
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

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <KpiCard
          label="Coût total"
          value={decision.cout_final}
          icon={Wallet}
          delay={60}
        />
        <KpiCard
          label="Surface allouée"
          value={totalHa}
          icon={Sprout}
          delay={140}
          format="ha"
        />
        <KpiCard
          label="Cultures actives"
          value={allocations.length}
          icon={LineChart}
          accent
          delay={220}
          format="int"
        />
      </div>

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
