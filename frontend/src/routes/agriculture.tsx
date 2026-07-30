import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ScoreGauge } from "@/components/ScoreGauge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sprout, Droplets, FlaskConical, Sun, ChevronRight, Satellite, Layers, Info, TrendingUp } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/agriculture")({
  head: () => ({
    meta: [
      { title: "Conseiller Agricole — AgriGuide" },
      { name: "description", content: "Analyse du sol, données satellite et top 5 des cultures recommandées pour votre parcelle." },
      { property: "og:title", content: "Conseiller Agricole — AgriGuide" },
      { property: "og:description", content: "Découvrez les cultures les plus adaptées à votre terrain." },
    ],
  }),
  component: Page,
});

const crops = [
  { name: "Blé tendre d'hiver", score: 94, why: "Sol argilo-calcaire idéal, rotation favorable", yield: "7,2 t/ha", margin: "+ 890 €/ha", water: "Modéré", fert: "Azoté N120", pest: "Traitement fongicide léger" },
  { name: "Colza", score: 88, why: "Bonne tolérance au climat local", yield: "3,5 t/ha", margin: "+ 720 €/ha", water: "Faible", fert: "Soufre + N", pest: "Piège méligèthes recommandé" },
  { name: "Orge de printemps", score: 82, why: "Débouché brasserie à 40 km", yield: "6,1 t/ha", margin: "+ 540 €/ha", water: "Modéré", fert: "N80", pest: "Peu d'intervention" },
  { name: "Tournesol", score: 76, why: "Faible besoin en eau", yield: "2,8 t/ha", margin: "+ 610 €/ha", water: "Faible", fert: "Modérée", pest: "Surveillance oiseaux" },
  { name: "Lentille verte", score: 71, why: "Prime légumineuse + rotation", yield: "1,3 t/ha", margin: "+ 480 €/ha", water: "Faible", fert: "Aucun N", pest: "Très peu d'interventions" },
];

function Page() {
  const [open, setOpen] = useState<null | (typeof crops)[number]>(null);
  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-2">
        <div className="h-11 w-11 rounded-2xl bg-harvest/15 text-harvest flex items-center justify-center">
          <Sprout className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">Conseiller Agricole</h1>
          <p className="text-muted-foreground mt-1">Ferme des Prés — 32 hectares</p>
        </div>
      </div>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {/* Analyse du sol */}
        <div className="card-soft p-6">
          <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            <Layers className="h-4 w-4" />
            Analyse du sol
          </div>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <SoilMetric value={72} color="var(--color-primary)" title="pH" subtitle="6,8 — équilibré" />
            <SoilMetric value={64} color="oklch(0.65 0.16 45)" title="Matière organique" subtitle="2,9%" />
            <SoilMetric value={81} color="var(--color-primary)" title="Azote" subtitle="Bon niveau" />
            <SoilMetric value={58} color="var(--color-sky)" title="Drainage" subtitle="Moyen" />
          </div>
        </div>

        {/* Image satellite */}
        <div className="card-soft p-6">
          <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            <Satellite className="h-4 w-4" />
            Image satellite (NDVI)
          </div>
          <div
            className="mt-5 aspect-square rounded-2xl relative overflow-hidden"
            style={{
              backgroundImage:
                "radial-gradient(circle at 30% 40%, oklch(0.72 0.18 140), transparent 55%), radial-gradient(circle at 70% 70%, oklch(0.55 0.16 140), transparent 55%), linear-gradient(135deg, oklch(0.8 0.12 130), oklch(0.58 0.16 140))",
            }}
          >
            <div className="absolute bottom-3 left-3 rounded-full bg-card/90 px-3 py-1 text-xs font-semibold">
              Végétation dense — 78%
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
            <span>Faible</span>
            <div className="flex-1 h-2 rounded-full" style={{ background: "linear-gradient(to right, oklch(0.75 0.15 30), oklch(0.8 0.15 80), oklch(0.6 0.16 140))" }} />
            <span>Forte</span>
          </div>
        </div>

        {/* Ce que ça veut dire */}
        <div className="rounded-3xl p-6 border border-border" style={{ background: "oklch(0.95 0.03 155)" }}>
          <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            <Info className="h-4 w-4" />
            Ce que ça veut dire
          </div>
          <p className="mt-4 font-display text-lg leading-relaxed text-foreground">
            «&nbsp;Votre parcelle Nord a une très bonne réserve en eau et un sol équilibré. Le drainage moyen suggère d'éviter les cultures très sensibles à l'excès d'eau.&nbsp;»
          </p>
          <ul className="mt-5 space-y-2.5 text-sm">
            <li className="flex items-center gap-2"><Sun className="h-4 w-4 text-harvest" /> Exposition sud-ouest, 6h de soleil moyen</li>
            <li className="flex items-center gap-2"><Droplets className="h-4 w-4 text-sky" /> Nappe à 3,4 m, réserve confortable</li>
            <li className="flex items-center gap-2"><TrendingUp className="h-4 w-4 text-primary" /> RPG : historique céréales 2019-2024</li>
          </ul>
        </div>
      </div>

      {/* Top 5 crops */}
      <div className="mt-10">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 className="font-display text-3xl font-semibold">Top 5 cultures recommandées</h2>
            <p className="text-muted-foreground mt-1">Classées par compatibilité, rendement estimé et marge nette.</p>
          </div>
          <div className="shrink-0 rounded-full border border-border bg-card px-4 py-1.5 text-sm font-medium">
            Saison 2026
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {crops.map((c, i) => (
            <div key={c.name} className="card-soft p-6 flex flex-col">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-harvest tracking-wide">#{i + 1}</div>
                  <div className="font-display text-2xl font-semibold mt-1">{c.name}</div>
                  <p className="text-sm text-muted-foreground mt-2">{c.why}</p>
                </div>
                <div className="h-14 w-14 rounded-full flex items-center justify-center font-display text-xl font-semibold shrink-0"
                  style={{ background: "oklch(0.88 0.05 150)", color: "oklch(0.35 0.08 150)" }}>
                  {c.score}
                </div>
              </div>
              <div className="mt-5 pt-5 border-t border-border grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">Rendement</div>
                  <div className="font-display text-lg mt-1">{c.yield}</div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">Marge nette</div>
                  <div className="font-display text-lg mt-1">{c.margin}</div>
                </div>
              </div>
              <Button variant="outline" size="sm" className="mt-5 rounded-xl self-start" onClick={() => setOpen(c)}>
                Voir les besoins <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <DialogContent className="rounded-3xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl">{open?.name}</DialogTitle>
            <DialogDescription>Besoins estimés par hectare et par saison.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 mt-2">
            <Row icon={Droplets} label="Irrigation" value={open?.water} />
            <Row icon={FlaskConical} label="Engrais" value={open?.fert} />
            <Row icon={Sun} label="Pesticides" value={open?.pest} />
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function Row({ icon: Icon, label, value }: { icon: typeof Droplets; label: string; value?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-secondary/50 p-4">
      <div className="h-10 w-10 rounded-xl bg-card flex items-center justify-center text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="font-medium">{value}</div>
      </div>
    </div>
  );
}

function SoilMetric({ value, color, title, subtitle }: { value: number; color: string; title: string; subtitle: string }) {
  const size = 96;
  const r = size / 2 - 8;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  return (
    <div className="flex flex-col items-center text-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={7} stroke="var(--color-muted)" fill="none" />
          <circle
            cx={size / 2} cy={size / 2} r={r} strokeWidth={7}
            stroke={color} fill="none" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
          <div className="font-display text-2xl font-semibold">{value}</div>
          <div className="text-[10px] text-muted-foreground mt-0.5">/ 100</div>
        </div>
      </div>
      <div className="mt-2 font-semibold text-sm">{title}</div>
      <div className="text-xs text-muted-foreground">{subtitle}</div>
    </div>
  );
}
