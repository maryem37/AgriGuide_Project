import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { Sprout, ScrollText, LineChart, Store, CloudSun, Droplets, Wind, ArrowRight, Sun } from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Tableau de bord — AgriMent" },
      { name: "description", content: "Vue d'ensemble de votre exploitation : météo, alertes et conseils du jour." },
      { property: "og:title", content: "Tableau de bord — AgriMent" },
      { property: "og:description", content: "Météo, alertes et conseillers en un coup d'œil." },
    ],
  }),
  component: Dashboard,
});

const advisors = [
  {
    to: "/agriculture" as const,
    title: "Conseiller Agricole",
    desc: "Découvrez les cultures les mieux adaptées à votre terrain.",
    icon: Sprout,
    color: "bg-harvest/15 text-harvest border-harvest/30",
  },
  {
    to: "/regulation" as const,
    title: "Conseiller Réglementaire",
    desc: "Aides, PAC, certifications — expliquées simplement.",
    icon: ScrollText,
    color: "bg-sky/25 text-sky-foreground border-sky/40",
  },
  {
    to: "/business" as const,
    title: "Conseiller Business",
    desc: "Simulez vos scénarios de culture et de revenus.",
    icon: LineChart,
    color: "bg-earth/15 text-earth border-earth/30",
  },
];

function Dashboard() {
  return (
    <AppShell>
      <div className="mb-8">
        <p className="text-sm text-muted-foreground">Bonjour Jean 👋</p>
        <h1 className="mt-1 font-display text-3xl md:text-4xl font-semibold">Comment se porte votre exploitation aujourd'hui ?</h1>
      </div>

      <AlertBanner tone="warning" title="Risque de gel cette nuit (Ferme des Prés)">
        Les températures descendront jusqu'à -2°C entre 3h et 6h. Protégez vos jeunes plants.
      </AlertBanner>

      {/* Weather */}
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="card-soft p-6 md:col-span-2 flex items-center justify-between bg-gradient-sky">
          <div>
            <div className="text-sm font-medium text-sky-foreground/80">Aujourd'hui — Chartres</div>
            <div className="mt-2 flex items-baseline gap-3">
              <span className="font-display text-5xl font-semibold text-sky-foreground">14°</span>
              <span className="text-sky-foreground/80">Éclaircies, vent modéré</span>
            </div>
            <div className="mt-4 flex gap-5 text-sm text-sky-foreground/90">
              <span className="inline-flex items-center gap-1.5"><Droplets className="h-4 w-4" /> 62% humidité</span>
              <span className="inline-flex items-center gap-1.5"><Wind className="h-4 w-4" /> 18 km/h</span>
              <span className="inline-flex items-center gap-1.5"><Sun className="h-4 w-4" /> UV 4</span>
            </div>
          </div>
          <CloudSun className="hidden md:block h-24 w-24 text-sky-foreground/80" />
        </div>

        <Link
          to="/marketplace"
          className="card-soft p-6 bg-gradient-warm hover:card-lift group flex flex-col justify-between"
        >
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-card px-3 py-1 text-xs font-semibold text-primary">
              <Store className="h-3.5 w-3.5" /> Mon marketplace
            </div>
            <div className="mt-3 font-display text-2xl font-semibold">3 annonces actives</div>
            <p className="text-sm text-muted-foreground mt-1">2 récoltes, 1 déchet valorisable</p>
          </div>
          <div className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:gap-2 transition-all">
            Ouvrir <ArrowRight className="h-4 w-4" />
          </div>
        </Link>
      </div>

      {/* Advisors */}
      <h2 className="font-display text-2xl font-semibold mt-10 mb-4">Vos trois conseillers</h2>
      <div className="grid gap-5 md:grid-cols-3">
        {advisors.map(({ to, title, desc, icon: Icon, color }) => (
          <Link key={to} to={to} className="card-soft p-6 hover:card-lift group">
            <div className={`h-14 w-14 rounded-2xl border flex items-center justify-center ${color}`}>
              <Icon className="h-7 w-7" />
            </div>
            <div className="mt-4 font-display text-xl font-semibold">{title}</div>
            <p className="text-sm text-muted-foreground mt-1">{desc}</p>
            <div className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:gap-2 transition-all">
              Ouvrir <ArrowRight className="h-4 w-4" />
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-10 rounded-3xl border border-border p-6 md:p-8 bg-card">
        <h3 className="font-display text-xl font-semibold">Conseil du jour</h3>
        <p className="text-muted-foreground mt-2 max-w-2xl">
          Vos parcelles de blé approchent du stade épiaison. C'est le bon moment pour surveiller
          l'apparition de la septoriose. Nous vous préviendrons si un risque est détecté.
        </p>
      </div>
    </AppShell>
  );
}
