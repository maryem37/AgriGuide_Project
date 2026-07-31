import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { MapPicker } from "@/components/MapPicker";
import { AlertBanner } from "@/components/AlertBanner";
import { ReportMarkdown } from "@/components/ReportMarkdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sprout,
  Droplets,
  FlaskConical,
  Sun,
  ChevronRight,
  Satellite,
  Layers,
  Info,
  TrendingUp,
  MapPin,
  Map as MapIcon,
  Ruler,
  Loader2,
  FileText,
  Bug,
  Leaf,
  CheckCircle2,
  CircleSlash,
  Users,
} from "lucide-react";
import { getCropVisual, scoreTone } from "@/lib/cropVisual";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth-context";
import { centroid } from "@/lib/terrain";
import {
  resolveParcel,
  getNeighbors,
  analyzeParcel,
  AgricultureApiError,
  type AnalyzeResponse,
  type SoilData,
  type VegetationData,
  type AgroCalcEstimate,
  type NeighborCropContext,
  type CropRecommendationOut,
  type ParcelResolution,
} from "@/lib/agricultureApi";
import { saveRealCropRecommendations, cultureLabel } from "@/lib/cropRecommendations";

export const Route = createFileRoute("/agriculture")({
  head: () => ({
    meta: [
      { title: "Conseiller Agricole — AgriMent" },
      { name: "description", content: "Analyse du sol, données satellite et top 5 des cultures recommandées pour votre parcelle." },
      { property: "og:title", content: "Conseiller Agricole — AgriMent" },
      { property: "og:description", content: "Découvrez les cultures les plus adaptées à votre terrain." },
    ],
  }),
  component: Page,
});

/** Nom lisible pour un code culture (RPG ou clé interne), avec repli sur la même règle que `taxonomy.get_display_name` côté backend. */
function displayCrop(code: string | null | undefined): string {
  if (!code) return "Non renseignée";
  const known = cultureLabel(code);
  if (known !== code) return known;
  return code.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function phQualifier(ph: number): string {
  if (ph < 5.5) return "acide";
  if (ph < 6.5) return "légèrement acide";
  if (ph <= 7.5) return "neutre";
  return "basique";
}

function fmtPct(v: number | null): string {
  return v === null ? "?" : `${v.toFixed(0)}%`;
}

function labelizeKey(key: string): string {
  const label = key.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  return String(value);
}

const FACTOR_LABELS: Record<string, string> = {
  ph: "pH du sol",
  temp: "Température",
  nitrogen: "Azote du sol",
  cec: "Capacité d'échange cationique",
  precip: "Précipitations (prévision)",
  workability: "Praticabilité du sol",
};

/** Reconstruit la contribution de chaque facteur (poids × score, voir `ml_service.py`) pour expliquer un score sans dupliquer la logique de scoring côté frontend. */
function topContributingFactors(featureImportance: Record<string, unknown>, limit = 2): string[] {
  const weights = featureImportance.weights as Record<string, number> | undefined;
  if (!weights || typeof weights !== "object") return [];
  const contributions = Object.entries(weights)
    .map(([factor, weight]) => {
      const score = featureImportance[`${factor}_score`];
      if (typeof score !== "number" || typeof weight !== "number") return null;
      return { factor, contribution: score * weight };
    })
    .filter((x): x is { factor: string; contribution: number } => x !== null)
    .sort((a, b) => b.contribution - a.contribution);
  return contributions.slice(0, limit).map((c) => FACTOR_LABELS[c.factor] ?? c.factor);
}

function topNeighborCrops(neighbors: NeighborCropContext, limit = 3): string {
  const entries = Object.entries(neighbors.crop_distribution_pct).sort((a, b) => b[1] - a[1]).slice(0, limit);
  if (entries.length === 0) return "aucune donnée exploitable";
  return entries.map(([code, pct]) => `${displayCrop(code)} (${Math.round(pct)}%)`).join(", ");
}

type SourceMode = "terrain" | "carte";

/** Doit rester en phase avec le défaut `radius_m` de `POST /agriculture/parcel/neighbors` côté backend. */
const NEIGHBORS_RADIUS_M = 800;

function Page() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const terrains = useMemo(() => user?.terrains ?? [], [user]);

  const [sourceMode, setSourceMode] = useState<SourceMode>(terrains.length > 0 ? "terrain" : "carte");
  const [selectedTerrainId, setSelectedTerrainId] = useState<string | undefined>(terrains[0]?.id);
  const [clickedPoint, setClickedPoint] = useState<[number, number] | null>(null);
  const [openCrop, setOpenCrop] = useState<CropRecommendationOut | null>(null);

  useEffect(() => {
    if (!selectedTerrainId && terrains[0]) setSelectedTerrainId(terrains[0].id);
  }, [terrains, selectedTerrainId]);

  const selectedTerrain = terrains.find((t) => t.id === selectedTerrainId) ?? null;

  const previewQuery = useQuery({
    queryKey: ["agriculture-parcel-preview", clickedPoint?.[0], clickedPoint?.[1]],
    queryFn: () => resolveParcel({ point: { lat: clickedPoint![0], lon: clickedPoint![1] } }),
    enabled: sourceMode === "carte" && clickedPoint !== null,
    retry: false,
  });

  const neighborsQuery = useQuery({
    queryKey: ["agriculture-neighbors-preview", clickedPoint?.[0], clickedPoint?.[1]],
    queryFn: () => getNeighbors({ point: { lat: clickedPoint![0], lon: clickedPoint![1] } }, NEIGHBORS_RADIUS_M),
    enabled: sourceMode === "carte" && clickedPoint !== null,
    retry: false,
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeParcel,
    onSuccess: (data) => {
      if (data.terrain_id) saveRealCropRecommendations(data.terrain_id, data.crop_recommendations);
    },
  });

  const analysis: AnalyzeResponse | null = analyzeMutation.data ?? null;

  function handleAnalyzeTerrain() {
    if (!selectedTerrain) return;
    const c = centroid(selectedTerrain.points);
    if (!c) return;
    analyzeMutation.mutate({ point: { lat: c[0], lon: c[1] }, terrain_id: selectedTerrain.id });
  }

  function handleAnalyzePoint() {
    if (!clickedPoint) return;
    analyzeMutation.mutate({ point: { lat: clickedPoint[0], lon: clickedPoint[1] } });
  }

  const overlayGeometry =
    sourceMode === "carte" && previewQuery.data?.geometry
      ? (previewQuery.data.geometry as unknown as { type: "Polygon"; coordinates: number[][][] } | { type: "MultiPolygon"; coordinates: number[][][][] })
      : null;

  const neighborGeometries =
    sourceMode === "carte" && neighborsQuery.data?.neighbors
      ? (neighborsQuery.data.neighbors.map((n) => n.geometry) as unknown as ({ type: "Polygon"; coordinates: number[][][] } | { type: "MultiPolygon"; coordinates: number[][][][] })[])
      : [];

  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-2">
        <div className="h-11 w-11 rounded-2xl bg-harvest/15 text-harvest flex items-center justify-center">
          <Sprout className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">Conseiller Agricole</h1>
          <p className="text-muted-foreground mt-1">
            {selectedTerrain ? `${selectedTerrain.nom ?? "Terrain"} — ${selectedTerrain.superficie_ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha` : "Sélectionnez ou analysez une parcelle"}
          </p>
        </div>
      </div>

      <div className="card-soft p-6 mt-6">
        <Tabs value={sourceMode} onValueChange={(v) => setSourceMode(v as SourceMode)}>
          <TabsList>
            <TabsTrigger value="terrain" disabled={terrains.length === 0}>
              <MapPin className="h-4 w-4 mr-1.5" /> Mon terrain
            </TabsTrigger>
            <TabsTrigger value="carte">
              <MapIcon className="h-4 w-4 mr-1.5" /> Explorer sur la carte
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {sourceMode === "terrain" && (
          <div className="mt-5">
            {terrains.length === 0 ? (
              <AlertBanner tone="warning" title="Aucun terrain déclaré">
                Ajoutez une parcelle depuis votre profil, ou utilisez l'onglet « Explorer sur la carte ».
              </AlertBanner>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                {terrains.length > 1 && (
                  <Select value={selectedTerrainId} onValueChange={setSelectedTerrainId}>
                    <SelectTrigger className="sm:w-64">
                      <SelectValue placeholder="Choisir un terrain" />
                    </SelectTrigger>
                    <SelectContent>
                      {terrains.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.nom ?? "Terrain"} ({t.superficie_ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                <Button
                  className="rounded-xl h-11"
                  disabled={!selectedTerrain || analyzeMutation.isPending}
                  onClick={handleAnalyzeTerrain}
                >
                  {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sprout className="h-4 w-4 mr-2" />}
                  Analyser {selectedTerrain?.nom ?? "ce terrain"}
                </Button>
              </div>
            )}
          </div>
        )}

        {sourceMode === "carte" && (
          <div className="mt-5 space-y-4">
            <MapPicker
              mode="point"
              onPoint={setClickedPoint}
              markerPosition={clickedPoint}
              overlayGeometry={overlayGeometry}
              neighborGeometries={neighborGeometries}
              height={420}
              hint="Cliquez sur une parcelle pour la résoudre (cadastre / RPG), puis lancez l'analyse."
            />
            {clickedPoint && (
              <div className="space-y-4">
                {previewQuery.isPending && (
                  <div className="rounded-2xl border border-border bg-secondary/40 p-4">
                    <Skeleton className="h-5 w-2/3" />
                  </div>
                )}
                {previewQuery.isError && (
                  <div className="rounded-2xl border border-border bg-secondary/40 p-4">
                    <p className="text-sm text-destructive">Impossible de résoudre la parcelle à ce point.</p>
                  </div>
                )}
                {previewQuery.data && (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <ParcelInfoCard parcel={previewQuery.data} />
                      {neighborsQuery.isPending ? (
                        <div className="card-soft p-5 space-y-3">
                          <Skeleton className="h-4 w-1/2" />
                          <Skeleton className="h-16 w-full" />
                        </div>
                      ) : neighborsQuery.data ? (
                        <NeighborsPreviewCard neighbors={neighborsQuery.data} radiusM={NEIGHBORS_RADIUS_M} />
                      ) : null}
                    </div>
                    <div className="flex justify-end">
                      <Button
                        className="rounded-xl shrink-0"
                        disabled={analyzeMutation.isPending}
                        onClick={handleAnalyzePoint}
                      >
                        {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sprout className="h-4 w-4 mr-2" />}
                        Analyser cette parcelle
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {analyzeMutation.isError && (
        <div className="mt-6">
          <AlertBanner tone="danger" title="L'analyse a échoué">
            {analyzeMutation.error instanceof AgricultureApiError
              ? analyzeMutation.error.message
              : "Une erreur inattendue est survenue."}
          </AlertBanner>
        </div>
      )}

      {analyzeMutation.isPending && (
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card-soft p-6 space-y-4">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          ))}
        </div>
      )}

      {analysis && (
        <>
          {analysis.warnings.length > 0 && (
            <div className="mt-6 space-y-3">
              {analysis.warnings.map((w, i) => (
                <AlertBanner key={i} tone="warning" title="À noter">
                  {w}
                </AlertBanner>
              ))}
            </div>
          )}

          <div className="mt-8 grid gap-5 md:grid-cols-3">
            <SoilCard soil={analysis.soil} />
            <NdviCard vegetation={analysis.vegetation} />
            <SummaryCard analysis={analysis} />
          </div>

          {analysis.agro_calc_top_crop && (
            <div className="mt-6">
              <AgroCalcCard
                estimate={analysis.agro_calc_top_crop}
                cropCode={analysis.crop_recommendations[0]?.culture ?? null}
              />
            </div>
          )}

          <div className="mt-10">
            <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
              <div>
                <h2 className="font-display text-3xl font-semibold">Top {analysis.crop_recommendations.length} cultures recommandées</h2>
                <p className="text-muted-foreground mt-1">Classées par compatibilité avec le sol et le climat local.</p>
              </div>
              {analysis.terrain_id && (
                <Button
                  variant="outline"
                  className="rounded-xl shrink-0"
                  onClick={() => navigate({ to: "/business" })}
                >
                  <TrendingUp className="h-4 w-4 mr-2" /> Utiliser dans Conseiller Business
                </Button>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {analysis.crop_recommendations.map((c) => (
                <CropCard key={c.culture} crop={c} onDetails={() => setOpenCrop(c)} />
              ))}
            </div>
          </div>

          {analysis.report ? (
            <div className="mt-10 card-soft p-6 md:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="h-11 w-11 rounded-2xl bg-primary/15 text-primary flex items-center justify-center shrink-0">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="font-display text-xl font-semibold">
                    Rapport
                    {(analysis.report.parcel_id ?? analysis.parcel.parcel_id) &&
                      ` — Réf. ${analysis.report.parcel_id ?? analysis.parcel.parcel_id}`}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Généré le {new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
                  </div>
                </div>
              </div>
              <ReportMarkdown markdown={analysis.report.report_markdown} />
              {analysis.report.unverified_figures.length > 0 && (
                <div className="mt-6 rounded-2xl bg-waste/10 border border-waste/30 p-4">
                  <div className="text-xs font-semibold text-waste-foreground uppercase tracking-wide">Chiffres non vérifiés à relire</div>
                  <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
                    {analysis.report.unverified_figures.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-10">
              <AlertBanner tone="info" title="Rapport IA non disponible">
                Le rapport agronomique détaillé (RAG + Mistral) n'a pas pu être généré pour cette analyse — vérifiez
                que <code>MISTRAL_API_KEY</code> est configurée et que le corpus documentaire a été indexé (voir{" "}
                <code>backend/agent_agriculture/README.md</code>). Les données ci-dessus (sol, satellite, cultures) restent valides.
              </AlertBanner>
            </div>
          )}
        </>
      )}

      <Dialog open={!!openCrop} onOpenChange={(v) => !v && setOpenCrop(null)}>
        <DialogContent className="rounded-3xl max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl">{openCrop ? displayCrop(openCrop.culture) : ""}</DialogTitle>
            <DialogDescription>Besoins estimés par hectare, calculés pour cette parcelle.</DialogDescription>
          </DialogHeader>
          {openCrop && (
            <div className="grid gap-3 mt-2">
              <NeedsSection title="Irrigation" icon={Droplets} data={openCrop.besoins_irrigation} />
              <NeedsSection title="Engrais azotés" icon={FlaskConical} data={openCrop.besoins_engrais} />
              <NeedsSection title="Pesticides" icon={Bug} data={openCrop.besoins_pesticides} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function SoilCard({ soil }: { soil: SoilData }) {
  const rows: { label: string; value: ReactNode }[] = [];
  if (soil.ph !== null) rows.push({ label: "pH", value: `${soil.ph.toFixed(1)} — ${phQualifier(soil.ph)}` });
  if (soil.organic_carbon_g_kg !== null) rows.push({ label: "Matière organique", value: `${soil.organic_carbon_g_kg.toFixed(1)} g/kg` });
  if (soil.nitrogen_g_kg !== null) rows.push({ label: "Azote total", value: `${soil.nitrogen_g_kg.toFixed(2)} g/kg` });
  if (soil.cec_cmolkg !== null) {
    rows.push({ label: "Capacité d'échange cationique", value: `${soil.cec_cmolkg.toFixed(1)} cmol+/kg` });
  }
  if (soil.bulk_density_kg_dm3 !== null) rows.push({ label: "Densité apparente", value: `${soil.bulk_density_kg_dm3.toFixed(2)} kg/dm³` });
  if (soil.coarse_fragments_pct !== null) rows.push({ label: "Éléments grossiers", value: `${soil.coarse_fragments_pct.toFixed(0)}%` });

  const hasTexture = soil.clay_pct !== null || soil.sand_pct !== null || soil.silt_pct !== null;

  return (
    <div className="card-soft p-6">
      <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
        <Layers className="h-4 w-4" />
        Analyse du sol
      </div>
      {rows.length === 0 && !hasTexture ? (
        <p className="mt-4 text-sm text-muted-foreground">{soil.warning ?? "Données de sol indisponibles pour cette parcelle."}</p>
      ) : (
        <div className="mt-4 space-y-2.5 text-sm">
          {hasTexture && (
            <div className="border-b border-border pb-2.5">
              <span className="text-muted-foreground">Texture</span>
              <div className="mt-1.5 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Argile</span>
                  <span className="font-medium">{fmtPct(soil.clay_pct)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Sable</span>
                  <span className="font-medium">{fmtPct(soil.sand_pct)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Limon</span>
                  <span className="font-medium">{fmtPct(soil.silt_pct)}</span>
                </div>
              </div>
            </div>
          )}
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between gap-3 border-b border-border pb-2 last:border-none">
              <span className="text-muted-foreground">{r.label}</span>
              <span className="font-medium text-right">{r.value}</span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 text-[11px] text-muted-foreground">Source : {soil.source === "soilgrids" ? "SoilGrids (ISRIC)" : soil.source}</div>
    </div>
  );
}

function NdviCard({ vegetation }: { vegetation: VegetationData }) {
  const unavailable = vegetation.source === "unavailable" || vegetation.mean_ndvi === null;
  const ndvi = vegetation.mean_ndvi ?? 0;
  const pct = Math.round(Math.min(1, Math.max(0, ndvi)) * 100);
  const label = ndvi < 0.2 ? "Sol nu / végétation clairsemée" : ndvi < 0.5 ? "Végétation modérée" : "Végétation dense et active";

  return (
    <div className="card-soft p-6">
      <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
        <Satellite className="h-4 w-4" />
        Image satellite (NDVI)
      </div>
      {unavailable ? (
        <p className="mt-4 text-sm text-muted-foreground">{vegetation.warning ?? "Donnée satellite indisponible pour cette parcelle."}</p>
      ) : (
        <>
          <div
            className="mt-5 aspect-square rounded-2xl relative overflow-hidden"
            style={{
              backgroundImage:
                "radial-gradient(circle at 30% 40%, oklch(0.72 0.18 140), transparent 55%), radial-gradient(circle at 70% 70%, oklch(0.55 0.16 140), transparent 55%), linear-gradient(135deg, oklch(0.8 0.12 130), oklch(0.58 0.16 140))",
            }}
          >
            <div className="absolute bottom-3 left-3 rounded-full bg-card/90 px-3 py-1 text-xs font-semibold">
              {label} — NDVI {ndvi.toFixed(2)}
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
            <span>Faible</span>
            <div className="flex-1 h-2 rounded-full relative" style={{ background: "linear-gradient(to right, oklch(0.75 0.15 30), oklch(0.8 0.15 80), oklch(0.6 0.16 140))" }}>
              <div
                className="absolute top-1/2 h-3 w-3 rounded-full bg-card border-2 border-foreground"
                style={{ left: `${pct}%`, transform: "translate(-50%, -50%)" }}
              />
            </div>
            <span>Forte</span>
          </div>
          {vegetation.observation_window_days !== null && (
            <p className="mt-3 text-[11px] text-muted-foreground">
              Fenêtre d'observation : {vegetation.observation_window_days} jours ({vegetation.valid_pixel_count ?? 0} pixels valides) — Sentinel-2.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function ParcelInfoCard({ parcel }: { parcel: ParcelResolution }) {
  if (!parcel.resolved) {
    return (
      <div className="card-soft p-5">
        <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase mb-3">
          <MapPin className="h-4 w-4" /> Parcelle
        </div>
        <p className="text-sm text-muted-foreground">
          {parcel.warning ?? "Aucune parcelle cadastrale trouvée à cet endroit."}
        </p>
      </div>
    );
  }

  const ref = parcel.parcel_id ?? parcel.rpg_id_parcel;
  const sourceLabel =
    parcel.source === "cadastre" ? "Cadastre (IGN)" : parcel.source === "rpg" ? "RPG" : "Tracé manuel";

  return (
    <div className="card-soft p-5">
      {ref && (
        <div className="text-xs font-semibold tracking-widest text-muted-foreground uppercase mb-3">Réf. {ref}</div>
      )}
      <div className="space-y-2.5 text-sm">
        <InfoRow icon={MapPin} label="Source" value={sourceLabel} />
        <InfoRow
          icon={Sprout}
          label="Statut"
          value={
            parcel.is_agricultural === true ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 text-primary px-2.5 py-0.5 text-xs font-semibold">
                <CheckCircle2 className="h-3.5 w-3.5" /> Terre agricole (RPG)
              </span>
            ) : parcel.is_agricultural === false ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-waste/15 text-waste-foreground px-2.5 py-0.5 text-xs font-semibold">
                <CircleSlash className="h-3.5 w-3.5" /> Non déclarée RPG
              </span>
            ) : (
              <span className="text-muted-foreground">Non vérifié</span>
            )
          }
        />
        <InfoRow icon={Leaf} label="Culture" value={displayCrop(parcel.crop_declared)} />
        <InfoRow
          icon={Ruler}
          label="Surface"
          value={parcel.area_ha !== null ? `${parcel.area_ha.toFixed(2)} ha` : "Inconnue"}
        />
      </div>
      {parcel.agricultural_note && parcel.is_agricultural === false && (
        <p className="mt-3 text-xs text-muted-foreground">{parcel.agricultural_note}</p>
      )}
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof Droplets; label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border pb-2.5 last:border-none last:pb-0">
      <span className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4 shrink-0" /> {label}
      </span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}

function NeighborsPreviewCard({ neighbors, radiusM }: { neighbors: NeighborCropContext; radiusM: number }) {
  const entries = Object.entries(neighbors.crop_distribution_pct).sort((a, b) => b[1] - a[1]);

  return (
    <div className="card-soft p-5">
      <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase mb-4">
        <Users className="h-4 w-4" />
        Cultures voisines — {neighbors.neighbor_count} parcelle{neighbors.neighbor_count > 1 ? "s" : ""} ({radiusM} m)
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">{neighbors.note}</p>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
          {entries.map(([crop, pct]) => (
            <div key={crop}>
              <div className="flex items-center justify-between gap-2 text-sm mb-1">
                <span className="truncate">{crop}</span>
                <span className="font-semibold text-primary shrink-0">{pct.toFixed(1)}%</span>
              </div>
              <Progress value={pct} className="h-1.5" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ analysis }: { analysis: AnalyzeResponse }) {
  const { parcel, dl_observation, neighbors } = analysis;
  return (
    <div className="rounded-3xl p-6 border border-border" style={{ background: "oklch(0.95 0.03 155)" }}>
      <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
        <Info className="h-4 w-4" />
        Résumé de la parcelle
      </div>
      <ul className="mt-4 space-y-2.5 text-sm">
        <li className="flex items-center gap-2">
          <Ruler className="h-4 w-4 text-primary shrink-0" />
          Surface : {parcel.area_ha ? `${parcel.area_ha.toFixed(2)} ha` : "inconnue"}
          {parcel.source !== "unresolved" && ` (source : ${parcel.source})`}
        </li>
        <li className="flex items-center gap-2">
          <Sun className="h-4 w-4 text-harvest shrink-0" />
          Culture déclarée (RPG) : {displayCrop(parcel.crop_declared)}
        </li>
        {parcel.is_agricultural === false && (
          <li className="flex items-center gap-2 text-destructive">
            <Info className="h-4 w-4 shrink-0" /> {parcel.agricultural_note ?? "Parcelle non reconnue comme agricole."}
          </li>
        )}
        {dl_observation.source !== "unavailable" && dl_observation.predicted_class_fr && (
          <li className="flex items-center gap-2">
            <Satellite className="h-4 w-4 text-sky shrink-0" />
            Culture observée par IA (satellite) : {dl_observation.predicted_class_fr}
            {dl_observation.confidence !== null && ` (confiance ${Math.round(dl_observation.confidence * 100)}%)`}
          </li>
        )}
        {neighbors && neighbors.neighbor_count > 0 && (
          <li className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary shrink-0" />
            Voisinage ({neighbors.neighbor_count} parcelles) : {topNeighborCrops(neighbors)}
          </li>
        )}
      </ul>
    </div>
  );
}

function AgroCalcCard({ estimate, cropCode }: { estimate: AgroCalcEstimate; cropCode: string | null }) {
  return (
    <div className="card-soft p-6">
      <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
        <FlaskConical className="h-4 w-4" />
        Fertilisation & irrigation — {displayCrop(cropCode)}
      </div>
      <div className="mt-5 grid sm:grid-cols-2 gap-4">
        <Row
          icon={FlaskConical}
          label="Dose d'azote conseillée"
          value={estimate.n_dose_kg_ha !== null ? `${formatValue(estimate.n_dose_kg_ha)} kg N/ha` : "N/A"}
        />
        <Row
          icon={Droplets}
          label="Besoin en irrigation"
          value={
            estimate.irrigation_need_mm !== null
              ? `${formatValue(estimate.irrigation_need_mm)} mm sur ${estimate.irrigation_window_days ?? "?"} j`
              : "N/A"
          }
        />
      </div>
      {(estimate.n_method_note || estimate.irrigation_method_note) && (
        <p className="mt-4 text-xs text-muted-foreground">
          {estimate.n_method_note} {estimate.irrigation_method_note}
        </p>
      )}
      {estimate.warning && <p className="mt-2 text-xs text-waste-foreground">{estimate.warning}</p>}
    </div>
  );
}

function CropCard({ crop, onDetails }: { crop: CropRecommendationOut; onDetails: () => void }) {
  const factors = topContributingFactors(crop.feature_importance);
  const nDose = crop.besoins_engrais?.n_dose_kg_ha;
  const cropLabel = displayCrop(crop.culture);
  const { icon: CropIcon, bg: iconBg, fg: iconFg } = getCropVisual(cropLabel);
  const tone = scoreTone(crop.score_compatibilite);
  return (
    <div className="card-soft p-6 flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex gap-3">
          <div
            className="h-11 w-11 rounded-2xl flex items-center justify-center shrink-0"
            style={{ background: iconBg, color: iconFg }}
          >
            <CropIcon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-harvest tracking-wide">#{crop.rang}</div>
            <div className="font-display text-2xl font-semibold mt-1">{cropLabel}</div>
            {factors.length > 0 && (
              <p className="text-sm text-muted-foreground mt-2">Facteurs favorables : {factors.join(", ")}</p>
            )}
          </div>
        </div>
        <div
          className="h-14 w-14 rounded-full flex items-center justify-center font-display text-xl font-semibold shrink-0"
          style={{ background: tone.bg, color: tone.fg }}
        >
          {Math.round(crop.score_compatibilite)}
        </div>
      </div>
      <div className="mt-5 pt-5 border-t border-border grid grid-cols-2 gap-4">
        <div>
          <div className="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">Cycle de culture</div>
          <div className="font-display text-lg mt-1">{crop.cycle_jours} jours</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase">Azote conseillé</div>
          <div className="font-display text-lg mt-1">{typeof nDose === "number" ? `${formatValue(nDose)} kg/ha` : "N/A"}</div>
        </div>
      </div>
      <Button variant="outline" size="sm" className="mt-5 rounded-xl self-start" onClick={onDetails}>
        Voir les besoins <ChevronRight className="h-4 w-4 ml-1" />
      </Button>
    </div>
  );
}

function NeedsSection({ title, icon: Icon, data }: { title: string; icon: typeof Droplets; data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([k]) => k !== "warning" && k !== "note");
  const note = data.note as string | undefined;
  const warning = data.warning as string | undefined;
  return (
    <div className="rounded-2xl bg-secondary/50 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold mb-2">
        <div className="h-8 w-8 rounded-xl bg-card flex items-center justify-center text-primary shrink-0">
          <Icon className="h-4 w-4" />
        </div>
        {title}
      </div>
      {entries.length === 0 && !warning ? (
        <p className="text-xs text-muted-foreground">Aucune donnée.</p>
      ) : (
        <div className="space-y-1.5 text-sm">
          {entries.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">{labelizeKey(k)}</span>
              <span className="font-medium text-right">{formatValue(v)}</span>
            </div>
          ))}
        </div>
      )}
      {note && <p className="mt-2 text-xs text-muted-foreground italic">{note}</p>}
      {warning && <p className="mt-2 text-xs text-waste-foreground">{warning}</p>}
    </div>
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
