import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { Reveal } from "@/components/motion/Reveal";
import { WeatherPanel } from "@/components/WeatherPanel";
import { listings } from "@/features/marketplace/data";
import { cn } from "@/lib/utils";
import {
  Sprout,
  ScrollText,
  LineChart,
  Store,
  ArrowRight,
  Check,
} from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Tableau de bord - AgriMent" },
      { name: "description", content: "Vue d'ensemble de votre exploitation : météo, alertes et conseils du jour." },
      { property: "og:title", content: "Tableau de bord - AgriMent" },
      { property: "og:description", content: "Météo, alertes et conseillers en un coup d'œil." },
    ],
  }),
  component: Dashboard,
});

/** Même parcours que la landing - agriculture → business → réglementation. */
const advisors = [
  {
    to: "/agriculture" as const,
    step: 1,
    title: "Conseiller agricole",
    body: "Nous analysons votre parcelle, le sol, le climat et les signaux du vivant - dont les insectes auxiliaires - pour recommander les meilleures cultures.",
    image: "/img/journey/agriculture.jpg",
    icon: Sprout,
    accent: "#C46A2B",
    accentSoft: "rgba(196, 106, 43, 0.14)",
    points: [
      "Analyse du sol",
      "Lecture parcelle & climat",
      "Insectes auxiliaires",
      "Top cultures recommandées",
    ],
  },
  {
    to: "/business" as const,
    step: 2,
    title: "Conseiller business",
    body: "Équilibrez budget, étude de marché et risque pour obtenir des scénarios rentables et une vision claire de vos hectares.",
    image: "/img/journey/business.jpg",
    icon: LineChart,
    accent: "#2B6CB0",
    accentSoft: "rgba(43, 108, 176, 0.14)",
    points: [
      "3 scénarios optimisés",
      "Score de matching",
      "Allocation des hectares",
      "Profit & risque estimés",
    ],
  },
  {
    to: "/regulation" as const,
    step: 3,
    title: "Conseiller réglementaire",
    body: "Indiquez votre situation. Obtenez les règles applicables, les certifications, les aides et le cadre à respecter - sans jargon.",
    image: "/img/journey/regulation.jpg",
    icon: ScrollText,
    accent: "#2F5230",
    accentSoft: "rgba(47, 82, 48, 0.12)",
    points: [
      "Cadre légal par région",
      "Certifications qualité",
      "Aides & subventions",
      "Obligations expliquées clairement",
    ],
  },
] as const;

const myListings = listings.filter((l) => l.mine);
const myRecoltes = myListings.filter((l) => l.kind === "recolte").length;
const myDechets = myListings.filter((l) => l.kind === "dechet").length;

function Dashboard() {
  return (
    <AppShell>
      <div className="landing-rise mb-8">
        <p className="text-sm text-muted-foreground">Bonjour Jean 👋</p>
        <h1 className="mt-1 font-display text-3xl md:text-4xl font-semibold">
          Comment se porte votre exploitation aujourd'hui ?
        </h1>
      </div>

      <Reveal delay={80}>
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
            className="group zoom-media nudge-x relative flex h-full min-h-[280px] w-full flex-col overflow-hidden rounded-3xl bg-card shadow-[0_12px_40px_-24px_rgba(28,43,28,0.45)] ring-1 ring-border/80 transition-all duration-400 hover:-translate-y-1 hover:shadow-[0_22px_48px_-20px_rgba(28,43,28,0.4)]"
          >
            {/* Photo collage of active listings */}
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
                className="pointer-events-none absolute inset-0 bg-gradient-to-t from-card via-card/20 to-transparent"
                aria-hidden
              />
              <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-primary shadow-sm backdrop-blur-sm">
                <Store className="h-3.5 w-3.5" />
                Marketplace
              </span>
            </div>

            <div className="relative flex flex-1 flex-col px-5 pb-5 pt-1">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Vos annonces
              </p>
              <div className="mt-1 font-display text-2xl font-semibold tracking-tight">
                {myListings.length} annonces actives
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {myRecoltes} récolte{myRecoltes > 1 ? "s" : ""}
                {myDechets > 0
                  ? `, ${myDechets} déchet${myDechets > 1 ? "s" : ""} valorisable${myDechets > 1 ? "s" : ""}`
                  : ""}
              </p>

              <ul className="mt-3 space-y-2">
                {myListings.slice(0, 3).map((l) => (
                  <li key={l.id} className="flex items-center gap-2.5 text-sm">
                    <span className="h-8 w-8 shrink-0 overflow-hidden rounded-lg ring-1 ring-border/60">
                      <img src={l.image} alt="" className="h-full w-full object-cover" />
                    </span>
                    <span className="min-w-0 flex-1 truncate font-medium">{l.title}</span>
                    <span className="shrink-0 text-xs font-semibold text-primary">{l.price}</span>
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

      {/* Advisors - même carte que « Votre parcours conseil » */}
      <div className="mt-10">
        <Reveal className="max-w-2xl">
          <h2 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
            Vos trois conseillers
          </h2>
          <p className="mt-2 text-muted-foreground">
            Trois modules qui s’enchaînent - chacun s’appuie sur le précédent.
          </p>
        </Reveal>

        <div className="mt-6 grid gap-6 md:grid-cols-3">
          {advisors.map((step, i) => {
            const Icon = step.icon;
            return (
              <Reveal key={step.to} from="up" delay={i * 140} className="flex">
                <Link
                  to={step.to}
                  className="group zoom-media nudge-x flex flex-1 flex-col overflow-hidden rounded-2xl bg-card shadow-[0_8px_30px_-18px_rgba(28,43,28,0.35)] ring-1 ring-border/80 transition-all duration-400 hover:-translate-y-1.5 hover:shadow-[0_22px_48px_-20px_rgba(28,43,28,0.45)]"
                >
                  <div className="relative aspect-[16/10] overflow-hidden">
                    <img
                      src={step.image}
                      alt=""
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                    <div
                      className="absolute inset-0 opacity-100 transition-opacity duration-500 group-hover:opacity-0"
                      style={{
                        background:
                          "linear-gradient(180deg, rgba(28,43,28,0) 45%, rgba(28,43,28,0.28) 100%)",
                      }}
                      aria-hidden
                    />
                    <div className="absolute left-3 top-3 flex items-center gap-2">
                      <span
                        className="relative flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white shadow-sm transition-transform duration-400 group-hover:scale-110"
                        style={{ backgroundColor: step.accent }}
                      >
                        {step.step}
                      </span>
                      <span className="rounded-full bg-white/95 px-3 py-1 text-xs font-semibold text-foreground shadow-sm backdrop-blur-sm">
                        Étape {step.step} sur 3
                      </span>
                    </div>
                    <span className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-400 group-hover:-translate-y-1 group-hover:rotate-6">
                      <Icon className="h-5 w-5" style={{ color: step.accent }} />
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col p-5 md:p-6">
                    <h3 className="font-display text-xl font-semibold tracking-tight">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {step.body}
                    </p>
                    <ul className="mt-5 space-y-2.5">
                      {step.points.map((point) => (
                        <li
                          key={point}
                          className="flex items-start gap-2.5 text-sm text-foreground/80"
                        >
                          <span
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-transform duration-300 group-hover:scale-110"
                            style={{ backgroundColor: step.accentSoft, color: step.accent }}
                          >
                            <Check className="h-3 w-3" strokeWidth={3} />
                          </span>
                          {point}
                        </li>
                      ))}
                    </ul>
                    <span
                      className={cn(
                        "mt-6 inline-flex items-center gap-1.5 text-sm font-semibold",
                        "opacity-80 transition group-hover:opacity-100",
                      )}
                      style={{ color: step.accent }}
                    >
                      Ouvrir <ArrowRight className="nudge-target h-4 w-4" />
                    </span>
                  </div>
                </Link>
              </Reveal>
            );
          })}
        </div>
      </div>

      <Reveal from="blur" className="mt-10">
        <div className="relative overflow-hidden rounded-3xl border border-border p-6 md:p-8 bg-card">
          <Sprout
            className="pointer-events-none absolute -bottom-6 -right-4 h-40 w-40 text-primary/06"
            aria-hidden
          />
          <h3 className="relative font-display text-xl font-semibold">Conseil du jour</h3>
          <p className="relative text-muted-foreground mt-2 max-w-2xl">
            Vos parcelles de blé approchent du stade épiaison. C'est le bon moment pour surveiller
            l'apparition de la septoriose. Nous vous préviendrons si un risque est détecté.
          </p>
        </div>
      </Reveal>
    </AppShell>
  );
}
