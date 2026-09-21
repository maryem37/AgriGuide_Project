import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ShieldAlert,
  CloudRain,
  Sun,
  PieChart,
  FileText,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Info,
  ExternalLink,
  Sliders,
  DollarSign,
  TrendingDown,
  Layers,
} from "lucide-react";
import {
  fetchClimateRisk,
  fetchClimateRiskReportHtml,
  fetchCropMix,
  type ClimateRiskResponse,
  type CropMixResponse,
} from "@/lib/riskApi";
import { useAuth } from "@/lib/auth-context";
import { AlertBanner } from "@/components/AlertBanner";

export const Route = createFileRoute("/risk")({
  head: () => ({
    meta: [
      { title: "Agent Risk Analyst - Belhsen et al. (2026) | AgriGuide" },
      {
        name: "description",
        content:
          "Évaluation scientifiquement fondée des risques climatiques (SPI/SPEI/NDVI) et optimisation d'assolement.",
      },
    ],
  }),
  component: RiskPage,
});

function RiskPage() {
  const { token } = useAuth();

  // Climate Risk Form State
  const [lat, setLat] = useState<number>(48.8566);
  const [lon, setLon] = useState<number>(2.3522);
  const [cropType, setCropType] = useState<string>("ble_tendre");
  const [parcelId, setParcelId] = useState<string>("PARCELLE-001");
  const [ndviCurrent, setNdviCurrent] = useState<number>(0.42);
  const [climateResult, setClimateResult] = useState<ClimateRiskResponse | null>(null);
  const [reportHtml, setReportHtml] = useState<string | null>(null);

  // Crop Mix Form State
  const [terrainId, setTerrainId] = useState<string>("TERRAIN-CENTRE-01");
  const [superficieHa, setSuperficieHa] = useState<number>(25.0);
  const [budgetEur, setBudgetEur] = useState<number>(15000);
  const [cropMixResult, setCropMixResult] = useState<CropMixResponse | null>(null);

  // Climate Risk Mutation
  const climateMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Veuillez vous connecter");
      const res = await fetchClimateRisk(
        {
          lat,
          lon,
          crop_type: cropType,
          parcel_id: parcelId,
          ndvi_current: ndviCurrent,
        },
        token
      );
      return res;
    },
    onSuccess: (data) => {
      setClimateResult(data);
    },
  });

  // HTML Report Mutation
  const reportMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Veuillez vous connecter");
      const html = await fetchClimateRiskReportHtml(
        {
          lat,
          lon,
          crop_type: cropType,
          parcel_id: parcelId,
          ndvi_current: ndviCurrent,
        },
        token
      );
      return html;
    },
    onSuccess: (html) => {
      setReportHtml(html);
      const win = window.open("", "_blank");
      if (win) {
        win.document.write(html);
        win.document.close();
      }
    },
  });

  // Crop Mix Mutation
  const cropMixMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Veuillez vous connecter");
      const res = await fetchCropMix(
        {
          terrain_id: terrainId,
          superficie_disponible_ha: superficieHa,
          budget_input: budgetEur,
          crop_recommendations: [
            {
              rang: 1,
              culture: "Blé tendre",
              score_compatibilite: 88,
              cycle_jours: 120,
              besoins_irrigation: {},
              besoins_engrais: {},
              besoins_pesticides: {},
              feature_importance: {},
            },
            {
              rang: 2,
              culture: "Maïs grain",
              score_compatibilite: 75,
              cycle_jours: 140,
              besoins_irrigation: {},
              besoins_engrais: {},
              besoins_pesticides: {},
              feature_importance: {},
            },
            {
              rang: 3,
              culture: "Tournesol",
              score_compatibilite: 82,
              cycle_jours: 110,
              besoins_irrigation: {},
              besoins_engrais: {},
              besoins_pesticides: {},
              feature_importance: {},
            },
          ],
        },
        token
      );
      return res;
    },
    onSuccess: (data) => {
      setCropMixResult(data);
    },
  });

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case "FAIBLE":
        return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
      case "MODÉRÉ":
        return "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30";
      case "ÉLEVÉ":
        return "bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30";
      case "CRITIQUE":
        return "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30";
      default:
        return "bg-secondary text-secondary-foreground";
    }
  };

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <PageHeader
          title="Agent Risk Analyst"
          subtitle="Évaluation scientifique du risque climatique (Belhsen et al., 2026) & Optimisation d'assolement HiGHS."
          icon={ShieldAlert}
        />

        {/* Banner scientific rigor */}
        <AlertBanner
          tone="info"
          title="Transparence Scientifique & Distinction de Modèles"
        >
          Seul le module de Risque Climatique Paramétrique (SPI / SPEI / NDVI decay) est directement adossé à la publication Belhsen et al. (2026, JRACR, doi:10.54560/jracr.v16i2.726). Les modules d'assolement (HHI) et de scénarios financiers sont des heuristiques d'ingénierie interne (V1).
        </AlertBanner>


        <Tabs defaultValue="climate" className="w-full">
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto mb-8">
            <TabsTrigger value="climate" className="flex items-center gap-2">
              <CloudRain className="h-4 w-4" />
              Risque Climatique (Belhsen et al.)
            </TabsTrigger>
            <TabsTrigger value="cropmix" className="flex items-center gap-2">
              <PieChart className="h-4 w-4" />
              Assolement & Diversification HHI
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: CLIMATE RISK */}
          <TabsContent value="climate" className="space-y-6">
            <Reveal>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl">
                    <Sliders className="h-5 w-5 text-primary" />
                    Paramètres de la Parcelle Agricole
                  </CardTitle>
                  <CardDescription>
                    Entrez la géolocalisation GPS et le suivi Sentinel-2 pour évaluer l'indice composite de sécheresse.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Identifiant Parcelle
                      </label>
                      <Input
                        value={parcelId}
                        onChange={(e) => setParcelId(e.target.value)}
                        placeholder="Ex: PARCELLE-NORD"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Latitude GPS
                      </label>
                      <Input
                        type="number"
                        step="0.0001"
                        value={lat}
                        onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Longitude GPS
                      </label>
                      <Input
                        type="number"
                        step="0.0001"
                        value={lon}
                        onChange={(e) => setLon(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Culture évaluée
                      </label>
                      <select
                        className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                        value={cropType}
                        onChange={(e) => setCropType(e.target.value)}
                      >
                        <option value="ble_tendre">Blé tendre</option>
                        <option value="mais_grain">Maïs grain</option>
                        <option value="orge_hiver">Orge d'hiver</option>
                        <option value="colza">Colza</option>
                        <option value="tournesol">Tournesol</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        NDVI Actuel (Sentinel-2)
                      </label>
                      <Input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={ndviCurrent}
                        onChange={(e) => setNdviCurrent(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div className="flex items-end gap-2">
                      <Button
                        className="w-full gap-2"
                        onClick={() => climateMutation.mutate()}
                        disabled={climateMutation.isPending}
                      >
                        {climateMutation.isPending ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Calcul en cours...
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="h-4 w-4" />
                            Évaluer le Risque Climatique
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Reveal>

            {climateResult && (
              <Reveal>
                <div className="space-y-6">
                  {/* Executive Score Card */}
                  <Card className="border-l-4 border-l-primary">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <div>
                        <CardTitle className="text-2xl font-bold flex items-center gap-3">
                          Score de Risque Climatique Global : {climateResult.risk_score} / 100
                          <Badge className={getRiskBadgeColor(climateResult.risk_level)}>
                            {climateResult.risk_level}
                          </Badge>
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Parcelle {climateResult.parcel_id} • Culture {climateResult.crop_type}
                        </CardDescription>
                      </div>
                      <Button
                        variant="outline"
                        className="gap-2"
                        onClick={() => reportMutation.mutate()}
                        disabled={reportMutation.isPending}
                      >
                        {reportMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <FileText className="h-4 w-4 text-primary" />
                        )}
                        Télécharger / Imprimer le Rapport HTML
                      </Button>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Breakdown grid */}
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t">
                        <div className="p-4 rounded-lg bg-secondary/40 space-y-1">
                          <span className="text-xs text-muted-foreground font-mono uppercase">
                            Indice Pluviométrique (SPI 3m)
                          </span>
                          <div className="text-xl font-bold text-foreground">
                            {climateResult.risk_breakdown.spi_3m.toFixed(2)}
                          </div>
                          <span className="text-xs text-muted-foreground block">
                            Distribution Gamma ajustée
                          </span>
                        </div>
                        <div className="p-4 rounded-lg bg-secondary/40 space-y-1">
                          <span className="text-xs text-muted-foreground font-mono uppercase">
                            Bilan Hydrique (SPEI 3m)
                          </span>
                          <div className="text-xl font-bold text-foreground">
                            {climateResult.risk_breakdown.spei_3m.toFixed(2)}
                          </div>
                          <span className="text-xs text-muted-foreground block">
                            Pearson Type III (ET0 Hargreaves)
                          </span>
                        </div>
                        <div className="p-4 rounded-lg bg-secondary/40 space-y-1">
                          <span className="text-xs text-muted-foreground font-mono uppercase">
                            Stress Végétatif (NDVI Decay)
                          </span>
                          <div className="text-xl font-bold text-foreground">
                            {(climateResult.risk_breakdown.ndvi_decay * 100).toFixed(1)}%
                          </div>
                          <span className="text-xs text-muted-foreground block">
                            Décrochage canopée Sentinel-2
                          </span>
                        </div>
                        <div className="p-4 rounded-lg bg-primary/10 border border-primary/20 space-y-1">
                          <span className="text-xs text-primary font-mono uppercase font-semibold">
                            Indice Composite
                          </span>
                          <div className="text-xl font-bold text-primary">
                            {climateResult.risk_breakdown.composite_index.toFixed(2)}
                          </div>
                          <span className="text-xs text-muted-foreground block">
                            0.45 SPI + 0.40 SPEI - 0.15 NDVI
                          </span>
                        </div>
                      </div>

                      {/* Insurance recommendation block */}
                      <div className="p-4 rounded-xl bg-card border shadow-sm space-y-3 mt-4">
                        <h4 className="font-semibold text-sm flex items-center gap-2 text-foreground">
                          <ShieldAlert className="h-4 w-4 text-emerald-500" />
                          Recommandation d'Assurance Paramétrique Sécheresse
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground block text-xs">Couverture suggérée :</span>
                            <span className="font-medium">{climateResult.insurance_recommendation.suggested_coverage}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-xs">Prime annuelle estimée :</span>
                            <span className="font-medium text-emerald-600 dark:text-emerald-400">
                              {climateResult.insurance_recommendation.estimated_annual_premium_eur_ha} € / ha / an
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-xs">Seuil d'indemnisation (Trigger) :</span>
                            <span className="font-medium">
                              {climateResult.insurance_recommendation.payout_trigger_threshold} (SPEI)
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground italic border-t pt-2 mt-2">
                          "{climateResult.insurance_recommendation.reasoning}"
                        </p>
                      </div>

                      {/* Citation badge */}
                      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
                        <Info className="h-4 w-4 shrink-0 mt-0.5" />
                        <div>
                          <strong>Référence Scientifique du Modèle :</strong> {climateResult.methodology_note}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </Reveal>
            )}
          </TabsContent>

          {/* TAB 2: CROP MIX */}
          <TabsContent value="cropmix" className="space-y-6">
            <Reveal>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl">
                    <PieChart className="h-5 w-5 text-primary" />
                    Optimisation d'Assolement Multi-Cultures (Solveur HiGHS)
                  </CardTitle>
                  <CardDescription>
                    Calcule la répartition optimale des hectares et l'indice Herfindahl-Hirschman (HHI) de diversification.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Identifiant Exploitation
                      </label>
                      <Input
                        value={terrainId}
                        onChange={(e) => setTerrainId(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Superficie totale disponible (ha)
                      </label>
                      <Input
                        type="number"
                        value={superficieHa}
                        onChange={(e) => setSuperficieHa(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                        Budget d'intrants disponible (€)
                      </label>
                      <Input
                        type="number"
                        value={budgetEur}
                        onChange={(e) => setBudgetEur(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                  <Button
                    className="mt-4 gap-2 w-full md:w-auto"
                    onClick={() => cropMixMutation.mutate()}
                    disabled={cropMixMutation.isPending}
                  >
                    {cropMixMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Optimisation HiGHS en cours...
                      </>
                    ) : (
                      <>
                        <PieChart className="h-4 w-4" />
                        Optimiser l'Assolement
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </Reveal>

            {cropMixResult && (
              <Reveal>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Résultat de l'Assolement Optimal ({cropMixResult.optimization_status})</span>
                      <Badge variant="outline">
                        Indice HHI : {cropMixResult.diversification_hhi_score.toFixed(0)} ({cropMixResult.diversification_label})
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="p-4 rounded-lg bg-secondary/40">
                        <span className="text-xs text-muted-foreground block">Surface Utilisée</span>
                        <span className="text-lg font-bold">
                          {cropMixResult.superficie_utilisee_ha} ha / {cropMixResult.superficie_totale_ha} ha
                        </span>
                      </div>
                      <div className="p-4 rounded-lg bg-secondary/40">
                        <span className="text-xs text-muted-foreground block">Budget Consommé</span>
                        <span className="text-lg font-bold">
                          {cropMixResult.budget_utilise_eur.toLocaleString()} €
                        </span>
                      </div>
                      <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <span className="text-xs text-emerald-600 dark:text-emerald-400 block font-semibold">
                          Profit Brut Estimé
                        </span>
                        <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                          {cropMixResult.profit_total_estime_eur.toLocaleString()} €
                        </span>
                      </div>
                      <div className="p-4 rounded-lg bg-secondary/40">
                        <span className="text-xs text-muted-foreground block">ROI Global</span>
                        <span className="text-lg font-bold">{cropMixResult.roi_global_pct.toFixed(1)}%</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h4 className="font-semibold text-sm">Répartition par Culture (Plafond Anti-Monoculture 50%)</h4>
                      <div className="divide-y rounded-lg border">
                        {cropMixResult.allocations.map((alloc) => (
                          <div key={alloc.culture} className="p-3 flex items-center justify-between text-sm">
                            <div className="font-medium">{alloc.culture}</div>
                            <div className="flex items-center gap-6">
                              <span>{alloc.hectares_alloues.toFixed(1)} ha ({alloc.pourcentage_surface.toFixed(1)}%)</span>
                              <span className="text-emerald-600 font-semibold">{alloc.profit_estime_eur.toLocaleString()} € profit</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-secondary/30 text-xs text-muted-foreground">
                      <strong>Note de transparence :</strong> {cropMixResult.methodology_note}
                    </div>
                  </CardContent>
                </Card>
              </Reveal>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}
