import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { Reveal } from "@/components/motion/Reveal";
import { WeatherPanel } from "@/components/WeatherPanel";
import { listings } from "@/features/marketplace/data";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import {
  Sprout,
  ScrollText,
  LineChart,
  Store,
  ArrowRight,
  CalendarDays,
  ChevronRight,
} from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Tableau de bord - AgriMent" },
      {
        name: "description",
        content: "Vue d'ensemble de votre exploitation : météo, alertes et conseils du jour.",
      },
      { property: "og:title", content: "Tableau de bord - AgriMent" },
      { property: "og:description", content: "Météo, alertes et conseillers en un coup d'œil." },
    ],
  }),
  component: Dashboard,
});

const ACTIONS = [
  {
    to: "/agriculture" as const,
    label: "Cultures",
    hint: "Analyser une parcelle",
    icon: Sprout,
  },
  {
    to: "/business" as const,
    label: "Budget",
    hint: "Comparer 3 scénarios",
    icon: LineChart,
  },
  {
    to: "/regulation" as const,
    label: "Règles",
    hint: "Aides & cadre légal",
    icon: ScrollText,
  },
  {
    to: "/aujourd-hui" as const,
    label: "Aujourd'hui",
    hint: "Briefing terrain",
    icon: CalendarDays,
  },
] as const;

const myListings = listings.filter((l) => l.mine);
const myRecoltes = myListings.filter((l) => l.kind === "recolte").length;
const myDechets = myListings.filter((l) => l.kind === "dechet").length;

function Dashboard() {
  const { user } = useAuth();
  const firstName = user?.nom?.split(" ")[0] ?? "Jean";

  return (
    <AppShell>
      <div className="landing-rise mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
            Exploitation · live
          </p>
          <h1 className="mt-2 font-display text-3xl md:text-[2.75rem] font-bold tracking-tight leading-[1.05]">
            Bonjour {firstName}.
            <br />
            <span className="text-primary/80">Voici le pouls du jour.</span>
          </h1>
        </div>
        <Link
          to="/aujourd-hui"
          className="nudge-x inline-flex items-center gap-2 self-start rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 md:self-auto"
        >
          Briefing du jour
          <ArrowRight className="nudge-target h-4 w-4" />
        </Link>
      </div>

      <Reveal delay={60}>
        <AlertBanner tone="warning" title="Risque de gel cette nuit (Ferme des Prés)">
          Les températures descendront jusqu'à -2°C entre 3h et 6h. Protégez vos jeunes plants.
        </AlertBanner>
      </Reveal>

      {/* Weather + marketplace */}
      <div className="mt-6 grid gap-4 md:grid-cols-3 md:items-stretch">
        <Reveal from="left" className="md:col-span-2 flex">
          <WeatherPanel className="w-full" />
        </Reveal>

        <Reveal from="right" delay={100} className="flex">
          <Link
            to="/marketplace"
            className="group zoom-media nudge-x surface-glass relative flex h-full min-h-[280px] w-full flex-col overflow-hidden rounded-2xl transition-all duration-400 hover:-translate-y-1"
          >
            <div className="relative grid h-36 grid-cols-3 gap-0.5 overflow-hidden sm:h-40">
              {myListings.slice(0, 3).map((l, i) => (
                <div key={l.id} className="relative overflow-hidden bg-muted">
                  <img
                    src={l.image}
                    alt=""
                    className="h-full w-full object-cover transition duration-700 group-hover:scale-105"
                    style={{ transitionDelay: `${i * 40}ms` }}
                    loading="lazy"
                  />
                </div>
              ))}
              <div
                className="pointer-events-none absolute inset-0 bg-gradient-to-t from-card via-card/30 to-transparent"
                aria-hidden
              />
            </div>

            <div className="relative flex flex-1 flex-col px-5 pb-5 pt-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                <Store className="h-3.5 w-3.5 text-primary" />
                Marché
              </div>
              <div className="mt-1 font-display text-2xl font-bold tracking-tight">
                {myListings.length} annonces
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {myRecoltes} récolte{myRecoltes > 1 ? "s" : ""}
                {myDechets > 0
                  ? ` · ${myDechets} déchet${myDechets > 1 ? "s" : ""}`
                  : ""}
              </p>

              <ul className="mt-3 space-y-2">
                {myListings.slice(0, 3).map((l) => (
                  <li key={l.id} className="flex items-center gap-2.5 text-sm">
                    <span className="h-8 w-8 shrink-0 overflow-hidden rounded-lg ring-1 ring-border/60">
                      <img src={l.image} alt="" className="h-full w-full object-cover" />
                    </span>
                    <span className="min-w-0 flex-1 truncate font-medium">{l.title}</span>
                    <span className="shrink-0 font-mono text-xs font-semibold text-primary">
                      {l.price}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="mt-auto pt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
                Voir le marché <ArrowRight className="nudge-target h-4 w-4" />
              </div>
            </div>
          </Link>
        </Reveal>
      </div>

      {/* Quick actions — operational, not journey pitch cards */}
      <div className="mt-10">
        <Reveal className="flex items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              Accès rapide
            </p>
            <h2 className="mt-1 font-display text-2xl md:text-3xl font-bold tracking-tight">
              Où aller ensuite&nbsp;?
            </h2>
          </div>
        </Reveal>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {ACTIONS.map((action, i) => {
            const Icon = action.icon;
            return (
              <Reveal key={action.to} from="up" delay={i * 70}>
                <Link
                  to={action.to}
                  className={cn(
                    "group surface-glass flex items-center gap-3 rounded-2xl p-4",
                    "transition-all duration-300 hover:-translate-y-0.5 hover:border-signal/50",
                  )}
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-signal transition-transform duration-300 group-hover:scale-105">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-display text-base font-bold tracking-tight">
                      {action.label}
                    </span>
                    <span className="block text-xs text-muted-foreground">{action.hint}</span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform duration-300 group-hover:translate-x-0.5 group-hover:text-foreground" />
                </Link>
              </Reveal>
            );
          })}
        </div>
      </div>

      <Reveal from="blur" className="mt-10">
        <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-primary px-6 py-7 md:px-8 md:py-8 text-primary-foreground">
          <div
            className="pointer-events-none absolute -right-10 -top-16 h-48 w-48 rounded-full bg-signal/25 blur-3xl"
            aria-hidden
          />
          <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="max-w-2xl">
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">
                Conseil du jour
              </p>
              <h3 className="mt-2 font-display text-xl md:text-2xl font-bold tracking-tight">
                Stade épiaison — surveillez la septoriose
              </h3>
              <p className="mt-2 text-sm text-primary-foreground/70 leading-relaxed">
                Vos parcelles de blé approchent du stade épiaison. C&apos;est le bon moment pour
                surveiller l&apos;apparition de la septoriose. Nous vous préviendrons si un risque
                est détecté.
              </p>
            </div>
            <Link
              to="/aujourd-hui"
              className="nudge-x inline-flex shrink-0 items-center gap-2 self-start rounded-xl bg-signal px-4 py-2.5 text-sm font-bold text-signal-foreground md:self-auto"
            >
              Ouvrir le briefing
              <ArrowRight className="nudge-target h-4 w-4" />
            </Link>
          </div>
        </div>
      </Reveal>
    </AppShell>
  );
}
