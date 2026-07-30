import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { Droplets, Bug, Sprout, CalendarDays, Wallet } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";

export const Route = createFileRoute("/aujourd-hui")({
  head: () => ({
    meta: [
      { title: "Aujourd'hui — AgriGuide" },
      { name: "description", content: "Conseils du jour, carnet de bord et suivi du budget pour votre exploitation." },
      { property: "og:title", content: "Aujourd'hui — AgriGuide" },
      { property: "og:description", content: "Vos actions du jour et le suivi de votre exploitation." },
    ],
  }),
  component: Page,
});

const tips = [
  { icon: Droplets, tone: "bg-sky/20 text-sky-foreground", title: "Irrigation légère", text: "3 mm recommandés sur la parcelle Est ce soir." },
  { icon: Bug, tone: "bg-waste/20 text-waste-foreground", title: "Alerte pucerons", text: "Surveillez la parcelle de colza — piégeage conseillé." },
  { icon: Sprout, tone: "bg-harvest/15 text-harvest", title: "Stade épiaison", text: "Votre blé entre en épiaison. Bilan azote dans 5 jours." },
];

const logbook = [
  { date: "Aujourd'hui, 07:12", title: "Passage de herse", detail: "Parcelle Nord — 4,2 ha" },
  { date: "Hier, 18:40", title: "Traitement fongicide", detail: "Blé tendre, dose 0,8 L/ha" },
  { date: "Lun. 22/07, 09:00", title: "Semis colza", detail: "Parcelle Est — 6 ha" },
  { date: "Dim. 21/07, 14:20", title: "Contrôle irrigation", detail: "Débit 12 L/min" },
];

const budgetData = [
  { mois: "Mars", prévu: 3200, réel: 3050 },
  { mois: "Avril", prévu: 4100, réel: 4300 },
  { mois: "Mai", prévu: 3800, réel: 3600 },
  { mois: "Juin", prévu: 2900, réel: 3100 },
  { mois: "Juil.", prévu: 2400, réel: 2200 },
];

function Page() {
  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-2">
        <div className="h-11 w-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
          <CalendarDays className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">Aujourd'hui</h1>
          <p className="text-muted-foreground mt-1">Mardi 28 juillet 2026</p>
        </div>
      </div>

      <div className="mt-6">
        <AlertBanner tone="warning" title="Vent fort attendu à 16h">
          Rafales jusqu'à 55 km/h — reportez les traitements après 20h.
        </AlertBanner>
      </div>

      {/* Tips */}
      <h2 className="font-display text-2xl font-semibold mt-10 mb-4">Vos conseils du jour</h2>
      <div className="grid gap-4 md:grid-cols-3">
        {tips.map(({ icon: Icon, tone, title, text }) => (
          <div key={title} className="card-soft p-5">
            <div className={`h-12 w-12 rounded-2xl flex items-center justify-center ${tone}`}>
              <Icon className="h-6 w-6" />
            </div>
            <div className="mt-3 font-display text-lg font-semibold">{title}</div>
            <p className="text-sm text-muted-foreground mt-1">{text}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 mt-10 lg:grid-cols-[1fr_1fr]">
        {/* Logbook */}
        <div className="card-soft p-6">
          <h2 className="font-display text-xl font-semibold">Carnet de bord</h2>
          <div className="mt-4 space-y-3">
            {logbook.map((l) => (
              <div key={l.date} className="flex gap-3 items-start">
                <div className="mt-1.5 h-2.5 w-2.5 rounded-full bg-primary shrink-0" />
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground">{l.date}</div>
                  <div className="font-medium">{l.title}</div>
                  <div className="text-sm text-muted-foreground">{l.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Budget */}
        <div className="card-soft p-6">
          <div className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">Coût réel vs. prévu</h2>
          </div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={budgetData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="mois" tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }} />
                <YAxis tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-card)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 12,
                  }}
                />
                <Legend />
                <Bar dataKey="prévu" fill="var(--color-secondary)" radius={[8, 8, 0, 0]} />
                <Bar dataKey="réel" fill="var(--color-primary)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
