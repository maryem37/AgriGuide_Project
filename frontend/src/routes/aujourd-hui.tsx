import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { useCountUp } from "@/components/motion/useCountUp";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  Cloud,
  CloudSun,
  Droplets,
  Sprout,
  Target,
  TrendingUp,
  Wallet,
  Wind,
} from "lucide-react";

export const Route = createFileRoute("/aujourd-hui")({
  head: () => ({
    meta: [
      { title: "Aujourd'hui - AgriMent" },
      {
        name: "description",
        content:
          "Briefing du jour : budget, allocation des cultures, météo, irrigation, alertes et tâches.",
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

const CROPS = [
  {
    id: "tomate",
    name: "Tomate",
    ha: 4.5,
    totalHa: 13,
    image: "/img/marketplace/tomate.jpg",
    pest: "Mildiou (Phytophthora infestans)",
    action: "Fongicide cuivre (mildiou)",
    risk: "medium" as const,
    irrigation: "Goutte-à-goutte",
  },
  {
    id: "pomme",
    name: "Pomme de terre",
    ha: 4,
    totalHa: 13,
    image: "/img/marketplace/pomme-de-terre.jpg",
    pest: "Doryphore (Leptinotarsa decemlineata)",
    action: "Anti-doryphore (spinosad)",
    risk: "medium" as const,
    irrigation: "Aspersion",
  },
  {
    id: "ble",
    name: "Blé tendre",
    ha: 4.5,
    totalHa: 13,
    image: "/img/marketplace/ble.jpg",
    pest: "Rouille brune (Puccinia triticina)",
    action: "Fongicide feuillage (prothioconazole)",
    risk: "low" as const,
    irrigation: "Pluvial (complément si sec)",
  },
];

const TASKS = [
  "Inspecter les parcelles de tomate pour détecter le mildiou",
  "Vérifier le programme d'irrigation goutte-à-goutte (tomate)",
  "Inspecter les parcelles de pomme de terre pour le doryphore",
  "Vérifier le programme d'aspersion (pomme de terre)",
  "Inspecter le blé tendre pour la rouille brune",
  "Vérifier l'irrigation complémentaire du blé si besoin",
];

function formatEuro(n: number) {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);
}

function KpiCard({
  label,
  value,
  icon: Icon,
  accent,
  delay,
}: {
  label: string;
  value: number;
  icon: typeof Wallet;
  accent?: boolean;
  delay: number;
}) {
  const [ref, displayed] = useCountUp(value, { duration: 1400 });
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
            <p
              className={cn(
                "text-sm",
                accent ? "text-primary/80" : "text-muted-foreground",
              )}
            >
              {label}
            </p>
            <p
              ref={ref}
              className="mt-2 font-display text-3xl font-semibold tracking-tight text-primary tabular-nums"
            >
              {formatEuro(displayed)}
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
        style={{ width: ready ? `${Math.round(ratio * 100)}%` : "0%" }}
      />
    </div>
  );
}

function Page() {
  const [done, setDone] = useState<Record<number, boolean>>({});
  const doneCount = Object.values(done).filter(Boolean).length;

  const toggle = (i: number) =>
    setDone((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <AppShell>
      <PageHeader
        icon={CalendarDays}
        title="Aujourd'hui"
        subtitle={
          <span className="inline-flex flex-wrap items-center gap-2">
            Mardi 4 août 2026
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              <span className="weather-live-dot !bg-primary" />
              Briefing du matin
            </span>
          </span>
        }
      />

      {/* KPIs */}
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <KpiCard label="Coût total" value={23625} icon={Wallet} delay={60} />
        <KpiCard
          label="Revenu projeté"
          value={371295}
          icon={TrendingUp}
          delay={140}
        />
        <KpiCard
          label="Bénéfice net"
          value={347670}
          icon={Target}
          accent
          delay={220}
        />
      </div>

      {/* Crop allocation */}
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
                  13 hectares répartis sur 3 cultures
                </p>
              </div>
            </div>
            {/* Visual field mosaic */}
            <div className="flex h-3 w-full max-w-[12rem] overflow-hidden rounded-full sm:w-48">
              {CROPS.map((c) => (
                <span
                  key={c.id}
                  className="h-full first:rounded-l-full last:rounded-r-full"
                  style={{
                    width: `${(c.ha / 13) * 100}%`,
                    backgroundImage: `url(${c.image})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                  }}
                  title={`${c.name} ${c.ha} ha`}
                />
              ))}
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {CROPS.map((crop, i) => (
              <Reveal key={crop.id} from="left" delay={160 + i * 100}>
                <div className="group flex items-center gap-3 md:gap-4">
                  <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl ring-1 ring-border/70 shadow-sm transition duration-500 group-hover:scale-105 group-hover:rotate-1 md:h-14 md:w-14">
                    <img
                      src={crop.image}
                      alt={crop.name}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <span className="font-semibold">{crop.name}</span>
                      <span className="text-sm font-medium tabular-nums text-muted-foreground">
                        {crop.ha} ha
                      </span>
                    </div>
                    <HectareBar ratio={crop.ha / crop.totalHa} />
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Reveal>

      {/* Daily briefing */}
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
                <p className="text-sm font-medium text-primary/70">Mardi 4 août</p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sky/40 px-3 py-1 text-xs font-semibold text-sky-foreground">
              <Bell className="h-3.5 w-3.5" />
              Quotidien
            </span>
          </div>

          {/* Weather strip */}
          <div className="relative mt-5 rounded-2xl bg-[#D7E8D9]/80 p-4 ring-1 ring-primary/10">
            <div className="mb-3 flex items-center gap-2 font-semibold text-primary">
              <CloudSun className="h-4 w-4 text-waste" />
              Météo du jour
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { icon: CloudSun, label: "26° / 14°", hint: "Max / min" },
                {
                  icon: Cloud,
                  label: "Éclaircies, orage possible",
                  hint: "Conditions",
                },
                { icon: Droplets, label: "8 mm", hint: "Précipitations" },
                { icon: Wind, label: "12 km/h", hint: "Vent" },
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
                    <p className="text-sm font-semibold text-foreground leading-snug">
                      {label}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Irrigation */}
          <div className="relative mt-3 flex gap-3 rounded-2xl bg-sky/25 p-4 ring-1 ring-sky/40">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky/50 text-sky-foreground">
              <Droplets className="h-5 w-5" />
            </span>
            <div>
              <h3 className="font-semibold text-primary">Gestion de l'irrigation</h3>
              <p className="mt-1 text-sm leading-relaxed text-foreground/80">
                L'humidité du sol est sous 40 % sur 2 parcelles. Prévoyez un
                goutte-à-goutte sur les tomates ce soir (18h00 à 20h00) pour limiter
                l'évaporation.
              </p>
            </div>
          </div>
        </div>
      </Reveal>

      {/* Pest alerts */}
      <div className="mt-8">
        <Reveal className="mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-waste" />
          <h2 className="font-display text-xl font-semibold tracking-tight">
            Alertes bioagresseurs
          </h2>
        </Reveal>
        <div className="grid gap-3">
          {CROPS.map((crop, i) => (
            <Reveal key={crop.id} from="up" delay={i * 100}>
              <div className="group flex flex-col gap-3 rounded-2xl bg-card p-3.5 ring-1 ring-border/80 transition-all duration-400 hover:-translate-y-0.5 hover:shadow-lift sm:flex-row sm:items-center sm:gap-4 sm:p-4">
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl ring-1 ring-border/60 transition duration-500 group-hover:scale-105">
                    <img
                      src={crop.image}
                      alt=""
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{crop.name}</span>
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide",
                          crop.risk === "medium"
                            ? "bg-waste/25 text-waste-foreground"
                            : "bg-harvest/20 text-harvest",
                        )}
                      >
                        {crop.risk === "medium" ? "Moyen" : "Faible"}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                      {crop.pest}
                    </p>
                  </div>
                </div>
                <p className="text-sm font-medium text-primary sm:max-w-[16rem] sm:text-right">
                  → {crop.action}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* Today's tasks */}
      <Reveal delay={100} className="mt-8">
        <div className="overflow-hidden rounded-3xl bg-card p-5 md:p-6 shadow-[0_12px_40px_-24px_rgba(28,43,28,0.35)] ring-1 ring-border/80">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <CheckCircle2 className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-display text-xl font-semibold tracking-tight">
                  Tâches du jour
                </h2>
                <p className="text-sm text-muted-foreground">
                  {doneCount}/{TASKS.length} terminée{doneCount > 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <div className="h-2 w-28 overflow-hidden rounded-full bg-primary/10 sm:w-36">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
                style={{ width: `${(doneCount / TASKS.length) * 100}%` }}
              />
            </div>
          </div>

          <ul className="mt-5 space-y-2">
            {TASKS.map((task, i) => {
              const checked = Boolean(done[i]);
              return (
                <li key={task}>
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
    </AppShell>
  );
}
