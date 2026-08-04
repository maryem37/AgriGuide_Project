import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  LineChart,
  Check,
  CheckCircle2,
  TrendingUp,
  MapPin,
  Ruler,
  Loader2,
  Info,
  Quote,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  fetchBusinessScenarios,
  confirmFarmerDecision,
  BusinessApiError,
  type BusinessAdvisorResponse,
  type BusinessScenario,
  type DetailCalculMetrique,
  type FarmerDecisionResponse,
} from "@/lib/businessApi";
import { MOCK_CROP_RECOMMENDATIONS, loadRealCropRecommendations, cultureLabel } from "@/lib/cropRecommendations";
import { saveFarmerDecision } from "@/lib/farmerDecision";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/business")({
  head: () => ({
    meta: [
      { title: "Conseiller Business - AgriMent" },
      {
        name: "description",
        content:
          "Simulez votre budget et comparez trois scénarios de cultures adaptés à votre exploitation.",
      },
      { property: "og:title", content: "Conseiller Business - AgriMent" },
      {
        property: "og:description",
        content: "Comparez trois scénarios pour tirer le meilleur de votre budget.",
      },
    ],
  }),
  component: Page,
});

const FALLBACK_SUPERFICIE_HA = 10;

/** Le farmer plante dans ~2 semaines par défaut ; ajustable plus tard depuis l'onboarding. */
function datePlantationPrevue(): string {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  return d.toISOString().slice(0, 10);
}

type RiskLevel = "Faible" | "Modéré" | "Élevé";

function riskLevel(risqueScoreNormalise: number): RiskLevel {
  if (risqueScoreNormalise <= 0.3) return "Faible";
  if (risqueScoreNormalise <= 0.55) return "Modéré";
  return "Élevé";
}

const riskColor: Record<RiskLevel, string> = {
  Faible: "bg-harvest/15 text-harvest border-harvest/30",
  Modéré: "bg-waste/20 text-waste-foreground border-waste/40",
  Élevé: "bg-destructive/10 text-destructive border-destructive/30",
};

function parseBudgetInput(raw: string): number | null {
  const cleaned = raw.replace(/\s/g, "").replace(",", ".");
  if (!cleaned) return null;
  const value = Number(cleaned);
  if (!Number.isFinite(value) || value <= 0) return null;
  return Math.round(value);
}

function Page() {
  const [budgetText, setBudgetText] = useState("25000");
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [report, setReport] = useState<BusinessAdvisorResponse | null>(null);

  const [selected, setSelected] = useState<BusinessScenario | null>(null);
  const [decision, setDecision] = useState<FarmerDecisionResponse | null>(null);
  const [detailScenario, setDetailScenario] = useState<BusinessScenario | null>(null);

  const { user } = useAuth();
  const terrains = useMemo(() => user?.terrains ?? [], [user]);
  // Le farmer peut avoir plusieurs terrains : la superficie disponible pour
  // ce scénario est la somme de toutes ses parcelles déclarées (Profil).
  const ha = useMemo(
    () => terrains.reduce((total, t) => total + (t.superficie_ha ?? 0), 0),
    [terrains],
  );
  const superficieDisponibleHa = ha >= 0.1 ? Math.round(ha * 100) / 100 : FALLBACK_SUPERFICIE_HA;
  const terrainId = terrains[0]?.id ?? "fallback-sans-terrain";

  // Liaison réelle avec backend/agent_business - POST /business/scenarios.
  // `crop_recommendations` vient de la dernière analyse réelle de l'agent
  // Agriculture pour ce terrain (voir routes/agriculture.tsx), mise en cache
  // via lib/cropRecommendations.ts ; tant qu'aucune analyse n'a été faite
  // pour ce terrain, on retombe sur des données factices pour rester
  // utilisable indépendamment.
  const cropRecommendations = useMemo(
    () => loadRealCropRecommendations(terrainId) ?? MOCK_CROP_RECOMMENDATIONS,
    [terrainId],
  );

  const decisionMutation = useMutation({
    mutationFn: confirmFarmerDecision,
    onSuccess: (data, variables) => {
      setDecision(data);
      saveFarmerDecision(data);
      const chosen = report?.scenarios.find(
        (s) => s.culture === variables.allocations[0]?.culture,
      );
      if (chosen) setSelected(chosen);
    },
  });

  const scenariosMutation = useMutation({
    mutationFn: (budget: number) =>
      fetchBusinessScenarios({
        terrain_id: terrainId,
        superficie_disponible_ha: superficieDisponibleHa,
        budget_input: budget,
        date_plantation_prevue: datePlantationPrevue(),
        crop_recommendations: cropRecommendations,
        nb_scenarios: 3,
      }),
    onSuccess: (data) => {
      setReport(data);
      setSelected(null);
      setDecision(null);
      decisionMutation.reset();
    },
  });

  function generateReport() {
    const budget = parseBudgetInput(budgetText);
    if (budget == null) {
      setBudgetError("Indiquez un budget valide en euros (ex. : 25000).");
      return;
    }
    setBudgetError(null);
    scenariosMutation.mutate(budget);
  }

  function chooseScenario(scenario: BusinessScenario) {
    decisionMutation.mutate({
      terrain_id: terrainId,
      superficie_disponible_ha: superficieDisponibleHa,
      allocations: [
        {
          scenario_id: `${scenario.culture}-scenario`,
          culture: scenario.culture,
          hectares_alloues: scenario.superficie_conseillee_ha,
        },
      ],
    });
  }

  function reset() {
    setSelected(null);
    setDecision(null);
    decisionMutation.reset();
  }

  if (selected && decision) {
    const risk = riskLevel(selected.risque_score);
    const allocation = decision.allocations[0];
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto text-center">
          <div className="mx-auto h-16 w-16 rounded-full bg-harvest/20 text-harvest flex items-center justify-center">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h1 className="mt-6 font-display text-3xl md:text-4xl font-semibold">
            Scénario confirmé
          </h1>
          <p className="mt-2 text-muted-foreground">
            Voici la répartition de vos hectares pour <b>{cultureLabel(selected.culture)}</b>.
          </p>
        </div>

        <div className="card-soft p-6 mt-8 max-w-2xl mx-auto">
          <div className="text-sm text-muted-foreground">
            Répartition confirmée (agent_business)
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-sm font-medium">
              <span>{cultureLabel(selected.culture)}</span>
              <span className="text-muted-foreground">{allocation.hectares_alloues} ha</span>
            </div>
            <div className="mt-1 h-3 rounded-full bg-secondary overflow-hidden">
              <div className="h-full bg-gradient-hero" style={{ width: "100%" }} />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-secondary/60 p-4">
              <div className="text-xs text-muted-foreground">Coût final</div>
              <div className="font-display text-2xl font-semibold">
                {allocation.cout_alloue.toLocaleString("fr-FR")} €
              </div>
            </div>
            <div className="rounded-2xl bg-secondary/60 p-4">
              <div className="text-xs text-muted-foreground">Récolte estimée</div>
              <div className="font-display text-2xl font-semibold">
                {new Date(allocation.date_maturite_prevue).toLocaleDateString("fr-FR")}
              </div>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <Badge className={`border ${riskColor[risk]}`}>Risque {risk}</Badge>
            <span className="text-xs text-muted-foreground">
              Décision #{decision.decision_id.slice(0, 8)}
            </span>
          </div>
        </div>

        <div className="mt-6 flex justify-center">
          <Button variant="outline" onClick={reset} className="rounded-xl">
            Choisir un autre scénario
          </Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        icon={LineChart}
        tone="earth"
        title="Conseiller Business"
        subtitle="Simulez vos revenus selon votre budget."
        className="mb-8"
      />

      <div className="grid gap-5 md:grid-cols-5">
        <Reveal from="up" delay={80} className="card-soft p-6 md:p-8 md:col-span-3">
          <div className="text-sm text-muted-foreground">Votre budget de départ</div>
          <div className="mt-4 flex flex-col sm:flex-row gap-3 sm:items-start">
            <div className="relative flex-1">
              <Input
                type="text"
                inputMode="decimal"
                value={budgetText}
                onChange={(e) => {
                  setBudgetText(e.target.value);
                  setBudgetError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    generateReport();
                  }
                }}
                placeholder="Ex. : 25000"
                aria-label="Budget en euros"
                className="h-12 rounded-xl pr-10 text-base font-display font-semibold"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                €
              </span>
              {budgetError && <p className="mt-1.5 text-xs text-destructive">{budgetError}</p>}
            </div>
            <Button
              type="button"
              className="h-12 rounded-xl shrink-0"
              disabled={scenariosMutation.isPending}
              onClick={generateReport}
            >
              {scenariosMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <LineChart className="h-4 w-4 mr-2" />
              )}
              Générer le rapport et les scénarios
            </Button>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Saisissez votre budget, puis lancez l’étude financière et les trois scénarios de
            cultures.
          </p>
        </Reveal>

        <Reveal from="up" delay={160} className="card-soft p-6 md:col-span-2 bg-gradient-sky text-sky-foreground">
          <div className="flex items-center gap-2 text-sm font-medium">
            <MapPin className="h-4 w-4" /> Vos terrains
          </div>
          {terrains.length > 0 ? (
            <>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="font-display text-4xl font-semibold">
                  {ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}
                </span>
                <span className="text-sky-foreground/80 inline-flex items-center gap-1 text-sm">
                  <Ruler className="h-4 w-4" /> hectares au total
                </span>
              </div>
              <div className="mt-3 space-y-1.5">
                {terrains.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between text-sm bg-card/20 rounded-lg px-3 py-1.5"
                  >
                    <span className="font-medium">{t.nom ?? "Terrain"}</span>
                    <span className="text-sky-foreground/80">
                      {t.superficie_ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-sky-foreground/90">
              Aucun terrain déclaré ({FALLBACK_SUPERFICIE_HA} ha utilisés par défaut). Ajoutez vos
              parcelles depuis votre profil pour un calcul basé sur votre superficie réelle.
            </p>
          )}
        </Reveal>
      </div>

      <Reveal as="h2" className="font-display text-2xl font-semibold mt-10 mb-4">
        Rapport financier et scénarios
      </Reveal>

      {scenariosMutation.isError && (
        <AlertBanner tone="danger" title="Agent Business injoignable">
          {scenariosMutation.error instanceof BusinessApiError
            ? scenariosMutation.error.message
            : "Une erreur inattendue est survenue."}
        </AlertBanner>
      )}

      {decisionMutation.isError && (
        <div className="mt-4">
          <AlertBanner tone="danger" title="La confirmation a échoué">
            {decisionMutation.error instanceof BusinessApiError
              ? decisionMutation.error.message
              : "Une erreur inattendue est survenue."}
          </AlertBanner>
        </div>
      )}

      {!report && !scenariosMutation.isPending && !scenariosMutation.isError && (
        <p className="text-sm text-muted-foreground">
          Aucun rapport pour l’instant. Indiquez votre budget puis cliquez sur « Générer le rapport
          et les scénarios ».
        </p>
      )}

      {scenariosMutation.isPending && (
        <div className="grid gap-5 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card-soft p-6 space-y-4">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
              <Skeleton className="h-12 w-full mt-6" />
            </div>
          ))}
        </div>
      )}

      {report && !scenariosMutation.isPending && (
        <>
          <div className="card-soft p-5 mb-5">
            <div className="text-sm font-medium">Synthèse du rapport financier</div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
              <div className="rounded-xl bg-secondary/60 p-3">
                <div className="text-xs text-muted-foreground">Budget analysé</div>
                <div className="font-display text-xl font-semibold">
                  {report.budget_input.toLocaleString("fr-FR")} €
                </div>
              </div>
              <div className="rounded-xl bg-secondary/60 p-3">
                <div className="text-xs text-muted-foreground">Meilleur profit estimé</div>
                <div className="font-display text-xl font-semibold text-primary">
                  {Math.max(...report.scenarios.map((s) => s.profit_estime)).toLocaleString(
                    "fr-FR",
                  )}{" "}
                  €
                </div>
              </div>
              <div className="rounded-xl bg-secondary/60 p-3">
                <div className="text-xs text-muted-foreground">Culture recommandée</div>
                <div className="font-display text-xl font-semibold">
                  {cultureLabel(report.scenarios[0]?.culture ?? "-")}
                </div>
              </div>
            </div>
          </div>

        <div className="grid gap-5 md:grid-cols-3">
          {report.scenarios.map((s, i) => {
            const risk = riskLevel(s.risque_score);
            const isBestScore = i === 0;
            const isChoosingThis =
              decisionMutation.isPending &&
              decisionMutation.variables?.allocations[0]?.culture === s.culture;
            return (
              <Reveal key={s.culture} from="up" delay={i * 120} className="card-soft p-6 flex flex-col">
                <div className="flex items-center justify-between">
                  <div className="font-display text-xl font-semibold">
                    {cultureLabel(s.culture)}
                  </div>
                  <Badge className={`border ${riskColor[risk]}`}>Risque {risk}</Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1">{s.risque_description}</p>

                <div className="mt-5 space-y-3 text-sm">
                  <Row label="Score de matching" value={`${s.matching_score.toFixed(1)} / 100`} />
                  <Row label="Surface conseillée" value={`${s.superficie_conseillee_ha} ha`} />
                  <Row
                    label="Rendement estimé"
                    value={`${s.quantite_par_ha.toLocaleString("fr-FR")} kg/ha`}
                  />
                  <Row
                    label="Récolte estimée"
                    value={new Date(s.etude_marche.date_recolte_estimee).toLocaleDateString(
                      "fr-FR",
                    )}
                  />
                  <Row
                    label="Profit estimé"
                    value={`${s.profit_estime.toLocaleString("fr-FR")} €`}
                    accent
                  />
                </div>

                <div className="mt-3 text-xs text-muted-foreground">
                  <span className="font-medium">Solution au risque :</span> {s.solution_risque}
                </div>

                <div className="mt-auto pt-6 space-y-2">
                  <Button
                    className="w-full rounded-xl h-12"
                    disabled={decisionMutation.isPending}
                    onClick={() => chooseScenario(s)}
                  >
                    {isChoosingThis ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="h-4 w-4 mr-2" />
                    )}
                    Choisir ce scénario
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full rounded-xl h-10"
                    onClick={() => setDetailScenario(s)}
                  >
                    <Info className="h-4 w-4 mr-2" /> Détails du calcul
                  </Button>
                </div>
                {isBestScore && (
                  <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-primary justify-center">
                    <TrendingUp className="h-3 w-3" /> Recommandé pour vous
                  </div>
                )}
              </Reveal>
            );
          })}
        </div>
        </>
      )}

      <Dialog open={!!detailScenario} onOpenChange={(open) => !open && setDetailScenario(null)}>
        <DialogContent className="rounded-3xl max-w-2xl max-h-[85vh] overflow-y-auto">
          {detailScenario && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-2xl">
                  Comment ces chiffres ont été calculés - {cultureLabel(detailScenario.culture)}
                </DialogTitle>
                <DialogDescription>
                  Calcul déterministe fait par l'agent Business (formule explicite, pas une
                  estimation du LLM).
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                <DetailSection
                  title="Score de matching"
                  detail={detailScenario.detail_calcul.score_matching}
                />
                <DetailSection
                  title="Surface conseillée"
                  detail={detailScenario.detail_calcul.surface_conseillee}
                />
                <DetailSection
                  title="Rendement estimé"
                  detail={detailScenario.detail_calcul.rendement_estime}
                />
                <DetailSection
                  title="Récolte estimée"
                  detail={detailScenario.detail_calcul.recolte_estimee}
                />
                <DetailSection
                  title="Profit estimé"
                  detail={detailScenario.detail_calcul.profit_estime}
                />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border pb-2 last:border-none">
      <span className="text-muted-foreground">{label}</span>
      <span className={accent ? "font-display text-lg font-semibold text-primary" : "font-medium"}>
        {value}
      </span>
    </div>
  );
}

/** Convertit une clé snake_case renvoyée par le backend en libellé lisible ("cout_total_eur_par_ha" -> "Cout total eur par ha"). */
function labelizeKey(key: string): string {
  const label = key.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function formatDetailValue(value: unknown): string {
  if (typeof value === "number") {
    return value.toLocaleString("fr-FR", { maximumFractionDigits: 4 });
  }
  if (typeof value === "string" && ISO_DATE_RE.test(value)) {
    return new Date(value).toLocaleDateString("fr-FR");
  }
  return String(value);
}

function DetailSection({ title, detail }: { title: string; detail: DetailCalculMetrique }) {
  return (
    <div className="rounded-2xl border border-border p-4">
      <div className="font-display text-lg font-semibold">{title}</div>
      <p className="mt-1 text-sm text-muted-foreground italic">{detail.formule}</p>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
        {Object.entries(detail.valeurs).map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between gap-2 border-b border-border/60 pb-1"
          >
            <span className="text-muted-foreground">{labelizeKey(key)}</span>
            <span className="font-medium text-right">{formatDetailValue(value)}</span>
          </div>
        ))}
      </div>

      <div className="mt-3 space-y-1">
        {detail.sources.map((source) => (
          <div key={source} className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <Quote className="h-3 w-3 mt-0.5 shrink-0" />
            <span>{source}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
