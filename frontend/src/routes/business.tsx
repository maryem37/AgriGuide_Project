import { createFileRoute, Link } from "@tanstack/react-router";
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
  Store,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  fetchBusinessScenarios,
  confirmFarmerDecision,
  BusinessApiError,
  type BusinessAdvisorResponse,
  type BusinessScenario,
  type DetailCalculMetrique,
  type FarmerDecisionResponse,
  type FarmerDecisionRequest,
} from "@/lib/businessApi";
import {
  getLatestAnalyzedTerrainId,
  loadRealCropRecommendations,
  cultureLabel,
} from "@/lib/cropRecommendations";
import { saveFarmerDecision } from "@/lib/farmerDecision";
import { useAuth } from "@/lib/auth-context";
import { MarketplaceWasteSuggestions } from "@/components/CropWasteValorization";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/business")({
  head: () => ({
    meta: [
      { title: "Conseiller Financier - AgriMent" },
      {
        name: "description",
        content:
          "Simulez votre budget et comparez trois scénarios de cultures adaptés à votre exploitation.",
      },
      { property: "og:title", content: "Conseiller Financier - AgriMent" },
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

  const { user, token } = useAuth();
  const terrains = useMemo(() => user?.terrains ?? [], [user]);
  const [selectedTerrainIds, setSelectedTerrainIds] = useState<string[]>([]);

  useEffect(() => {
    if (!terrains.length) {
      setSelectedTerrainIds([]);
      return;
    }
    setSelectedTerrainIds((current) => {
      const stillValid = current.filter((id) => terrains.some((t) => t.id === id));
      if (stillValid.length > 0) return stillValid;
      const analyzed = getLatestAnalyzedTerrainId();
      if (analyzed && terrains.some((t) => t.id === analyzed)) return [analyzed];
      return [terrains[0].id];
    });
  }, [terrains]);

  const selectedTerrains = useMemo(
    () => terrains.filter((t) => selectedTerrainIds.includes(t.id)),
    [terrains, selectedTerrainIds],
  );
  const ha = selectedTerrains.reduce((sum, t) => sum + (t.superficie_ha ?? 0), 0);
  const superficieDisponibleHa = ha >= 0.1 ? Math.round(ha * 100) / 100 : FALLBACK_SUPERFICIE_HA;

  // Primary terrain for persistence: prefer Agriculture-analyzed parcel among selection.
  const terrainId = useMemo(() => {
    const analyzed = getLatestAnalyzedTerrainId();
    if (analyzed && selectedTerrainIds.includes(analyzed)) return analyzed;
    for (const id of selectedTerrainIds) {
      if ((loadRealCropRecommendations(id) ?? []).length > 0) return id;
    }
    return selectedTerrainIds[0] ?? "fallback-sans-terrain";
  }, [selectedTerrainIds]);
  const terrainIdsKey = selectedTerrainIds.slice().sort().join(",");

  const cropRecommendations = useMemo(() => {
    for (const id of selectedTerrainIds) {
      const recs = loadRealCropRecommendations(id);
      if (recs && recs.length > 0) return recs;
    }
    return loadRealCropRecommendations(terrainId) ?? [];
  }, [selectedTerrainIds, terrainId]);

  function toggleTerrain(id: string) {
    setSelectedTerrainIds((current) => {
      if (current.includes(id)) {
        if (current.length === 1) return current;
        return current.filter((value) => value !== id);
      }
      return [...current, id];
    });
  }

  const decisionMutation = useMutation({
    mutationFn: (request: FarmerDecisionRequest) => {
      if (!token) throw new Error("Authentification requise.");
      return confirmFarmerDecision(request, token);
    },
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
    mutationFn: (budget: number) => {
      if (!token) throw new Error("Authentification requise.");
      return fetchBusinessScenarios({
        terrain_id: terrainId,
        terrain_ids: selectedTerrainIds,
        superficie_disponible_ha: superficieDisponibleHa,
        budget_input: budget,
        date_plantation_prevue: datePlantationPrevue(),
        crop_recommendations: cropRecommendations,
        nb_scenarios: 3,
      }, token);
    },
    onSuccess: (data) => {
      setReport(data);
      setSelected(null);
      setDecision(null);
      decisionMutation.reset();
    },
  });

  useEffect(() => {
    setReport(null);
    setSelected(null);
    setDecision(null);
    decisionMutation.reset();
    scenariosMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [terrainIdsKey]);

  function generateReport() {
    if (selectedTerrainIds.length === 0) {
      setBudgetError("Sélectionnez au moins un terrain.");
      return;
    }
    if (cropRecommendations.length === 0) {
      setBudgetError(
        "Analysez d'abord un des terrains sélectionnés dans le Conseiller Agriculture pour obtenir de vraies recommandations.",
      );
      return;
    }
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
      terrain_ids: selectedTerrainIds,
      superficie_disponible_ha: superficieDisponibleHa,
      allocations: [
        {
          scenario_id: scenario.id!,
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

        <MarketplaceWasteSuggestions culture={selected.culture} />

        <div className="mt-6 flex flex-col sm:flex-row justify-center gap-3">
          <Button variant="outline" onClick={reset} className="rounded-xl">
            Choisir un autre scénario
          </Button>
          <Button asChild className="rounded-xl">
            <Link to="/marketplace/nouveau" search={{ kind: "dechet", culture: selected.culture }}>
              <Store className="h-4 w-4 mr-2" />
              Aller à la marketplace
            </Link>
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
        title="Conseiller Financier"
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
              <p className="mt-2 text-xs text-sky-foreground/80">
                Sélectionnez une ou plusieurs parcelles
              </p>
              <div className="mt-3 max-h-44 space-y-2 overflow-y-auto pr-1">
                {terrains.map((t) => {
                  const checked = selectedTerrainIds.includes(t.id);
                  const isPrimary = t.id === terrainId;
                  return (
                    <label
                      key={t.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                        checked ? "bg-card/35 ring-1 ring-sky-foreground/25" : "bg-card/15 hover:bg-card/25",
                      )}
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleTerrain(t.id)}
                        className="border-sky-foreground/40 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">
                          {t.nom ?? "Terrain"}
                          {isPrimary ? " · analyse Agri" : ""}
                        </span>
                        <span className="text-xs text-sky-foreground/75">
                          {t.superficie_ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="font-display text-4xl font-semibold">
                  {ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}
                </span>
                <span className="text-sky-foreground/80 inline-flex items-center gap-1 text-sm">
                  <Ruler className="h-4 w-4" /> ha · {selectedTerrains.length} parcelle
                  {selectedTerrains.length > 1 ? "s" : ""}
                </span>
              </div>
              {cropRecommendations.length > 0 ? (
                <p className="mt-3 text-xs text-sky-foreground/85">
                  Analyse Agriculture disponible
                  ({cropRecommendations.length} culture
                  {cropRecommendations.length > 1 ? "s" : ""}).
                </p>
              ) : (
                <p className="mt-3 text-xs text-sky-foreground/85">
                  Aucune analyse Agriculture pour les terrains sélectionnés — analysez-en un
                  d’abord dans le Conseiller Agriculture.
                </p>
              )}
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
        <AlertBanner tone="danger" title="Agent Financier injoignable">
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
                  <Row
                    label="Compatibilité Agriculture"
                    value={`${s.score_compatibilite.toFixed(1)} / 100`}
                  />
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
                    label="Revenu brut"
                    value={`${s.indicateurs_financiers.revenu_brut_estime_eur.toLocaleString("fr-FR")} €`}
                  />
                  <Row
                    label="Coût total"
                    value={`${s.indicateurs_financiers.cout_total_estime_eur.toLocaleString("fr-FR")} €`}
                  />
                  <Row
                    label="Profit estimé"
                    value={`${s.profit_estime.toLocaleString("fr-FR")} €`}
                    accent
                  />
                  <Row
                    label="Marge / ROI"
                    value={`${s.indicateurs_financiers.profit_margin_pct.toFixed(1)} % / ${s.indicateurs_financiers.roi_pct.toFixed(1)} %`}
                  />
                  <Row
                    label="Écart au budget"
                    value={`${s.indicateurs_financiers.budget_gap_eur.toLocaleString("fr-FR")} €`}
                  />
                  <Row
                    label="Confiance données"
                    value={`${s.confiance_donnees.niveau} (${Math.round(s.confiance_donnees.score * 100)} %)`}
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
        <div className="mt-4 flex justify-end">
          <img
            src="/LABEL_AI%20GENERATED_black%20transparent.png"
            alt="Contenu généré par IA"
            className="h-16 w-auto"
          />
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
