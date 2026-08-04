import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { MapPicker } from "@/components/MapPicker";
import { AlertBanner } from "@/components/AlertBanner";
import { ReportMarkdown } from "@/components/ReportMarkdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
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
  Ruler,
  Loader2,
  FileText,
  Bug,
  Leaf,
  CheckCircle2,
  CircleSlash,
  Users,
  BookmarkPlus,
  Trash2,
  Cloud,
  CloudLightning,
  CloudRain,
  CloudFog,
  CloudSun,
  Snowflake,
  Wind,
  Droplet,
  Sunrise,
  Sunset,
  Thermometer,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
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
import { centroid, type LatLng } from "@/lib/terrain";
import {
  addTerrain,
  deleteTerrain,
  fetchMe,
  AuthApiError,
} from "@/lib/authApi";
import {
  resolveParcel,
  getNeighbors,
  analyzeParcel,
  AgricultureApiError,
  type AnalyzeResponse,
  type SoilData,
  type VegetationData,
  type WeatherData,
  type AgroCalcEstimate,
  type NeighborCropContext,
  type CropRecommendationOut,
  type ParcelResolution,
} from "@/lib/agricultureApi";
import { saveRealCropRecommendations, cultureLabel } from "@/lib/cropRecommendations";

type GeoPolygon =
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };

/** Convertit un contour terrain [lat,lng] en GeoJSON Polygon [lng,lat] pour la carte. */
function pointsToPolygon(points: LatLng[]): GeoPolygon | null {
  if (points.length < 3) return null;
  const ring = points.map(([lat, lng]) => [lng, lat]);
  const [fLng, fLat] = ring[0];
  const [lLng, lLat] = ring[ring.length - 1];
  if (fLng !== lLng || fLat !== lLat) ring.push([fLng, fLat]);
  return { type: "Polygon", coordinates: [ring] };
}

/** Extrait l'anneau extérieur d'une géométrie cadastre/RPG → points [lat,lng] pour l'API auth. */
function geometryToPoints(geometry: Record<string, unknown> | null | undefined): LatLng[] | null {
  if (!geometry || typeof geometry.type !== "string") return null;
  let ring: number[][] | undefined;
  if (geometry.type === "Polygon") {
    ring = (geometry.coordinates as number[][][])?.[0];
  } else if (geometry.type === "MultiPolygon") {
    ring = (geometry.coordinates as number[][][][])?.[0]?.[0];
  }
  if (!ring || ring.length < 3) return null;
  const points: LatLng[] = ring.map(([lng, lat]) => [lat, lng]);
  const first = points[0];
  const last = points[points.length - 1];
  if (first[0] === last[0] && first[1] === last[1]) points.pop();
  return points.length >= 3 ? points : null;
}

export const Route = createFileRoute("/agriculture")({
  head: () => ({
    meta: [
      { title: "Conseiller Agricole - AgriMent" },
      { name: "description", content: "Analyse du sol, données satellite et top 5 des cultures recommandées pour votre parcelle." },
      { property: "og:title", content: "Conseiller Agricole - AgriMent" },
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

/** Doit rester en phase avec le défaut `radius_m` de `POST /agriculture/parcel/neighbors` côté backend. */
const NEIGHBORS_RADIUS_M = 800;
const EXPLORE_VALUE = "__explore__";

function Page() {
  const navigate = useNavigate();
  const { user, token, setUser } = useAuth();
  const terrains = useMemo(() => user?.terrains ?? [], [user]);

  const [selectedTerrainId, setSelectedTerrainId] = useState<string | undefined>(terrains[0]?.id);
  /** "terrain" = sélection dans la liste ; "carte" = point cliqué (exploration). */
  const [selectionSource, setSelectionSource] = useState<"terrain" | "carte">(
    terrains.length > 0 ? "terrain" : "carte",
  );
  const [clickedPoint, setClickedPoint] = useState<[number, number] | null>(null);
  const [openCrop, setOpenCrop] = useState<CropRecommendationOut | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [savingTerrain, setSavingTerrain] = useState(false);
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTerrainId && terrains[0]) {
      setSelectedTerrainId(terrains[0].id);
      setSelectionSource("terrain");
    }
  }, [terrains, selectedTerrainId]);

  const selectedTerrain = terrains.find((t) => t.id === selectedTerrainId) ?? null;
  const terrainCentroid = selectedTerrain ? centroid(selectedTerrain.points) : null;

  const activePoint: [number, number] | null =
    selectionSource === "terrain" && terrainCentroid
      ? terrainCentroid
      : selectionSource === "carte"
        ? clickedPoint
        : null;

  const previewQuery = useQuery({
    queryKey: ["agriculture-parcel-preview", activePoint?.[0], activePoint?.[1], selectionSource],
    queryFn: () => resolveParcel({ point: { lat: activePoint![0], lon: activePoint![1] } }),
    enabled: activePoint !== null,
    retry: false,
  });

  const neighborsQuery = useQuery({
    queryKey: ["agriculture-neighbors-preview", activePoint?.[0], activePoint?.[1]],
    queryFn: () => getNeighbors({ point: { lat: activePoint![0], lon: activePoint![1] } }, NEIGHBORS_RADIUS_M),
    enabled: activePoint !== null,
    retry: false,
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeParcel,
    onSuccess: (data) => {
      setShowReport(false);
      if (data.terrain_id) saveRealCropRecommendations(data.terrain_id, data.crop_recommendations);
    },
  });

  const analysis: AnalyzeResponse | null = analyzeMutation.data ?? null;

  function handleSelectTerrain(value: string) {
    if (value === EXPLORE_VALUE) {
      setSelectionSource("carte");
      setSelectedTerrainId(undefined);
      return;
    }
    setSelectedTerrainId(value);
    setSelectionSource("terrain");
    setClickedPoint(null);
  }

  function handleMapPoint(point: [number, number]) {
    setClickedPoint(point);
    setSelectionSource("carte");
    setShowSaveForm(false);
    setTerrainError(null);
  }

  function handleAnalyze() {
    if (!activePoint) return;
    if (selectionSource === "terrain" && selectedTerrain) {
      analyzeMutation.mutate({
        point: { lat: activePoint[0], lon: activePoint[1] },
        terrain_id: selectedTerrain.id,
      });
      return;
    }
    analyzeMutation.mutate({ point: { lat: activePoint[0], lon: activePoint[1] } });
  }

  const terrainPolygon = selectionSource === "terrain" && selectedTerrain
    ? pointsToPolygon(selectedTerrain.points)
    : null;

  const overlayGeometry: GeoPolygon | null =
    terrainPolygon ??
    (selectionSource === "carte" && previewQuery.data?.geometry
      ? (previewQuery.data.geometry as unknown as GeoPolygon)
      : null);

  const neighborGeometries =
    neighborsQuery.data?.neighbors
      ? (neighborsQuery.data.neighbors.map((n) => n.geometry) as unknown as GeoPolygon[])
      : [];

  const mapCenter = activePoint ?? ([46.7, 2.5] as [number, number]);
  const mapZoom = activePoint ? 15 : 6;

  const selectValue =
    selectionSource === "terrain" && selectedTerrainId ? selectedTerrainId : EXPLORE_VALUE;

  const canSaveExplored =
    selectionSource === "carte" &&
    !!token &&
    !!previewQuery.data?.resolved &&
    !!geometryToPoints(previewQuery.data.geometry);

  async function handleSaveTerrain() {
    if (!token || !previewQuery.data?.resolved) return;
    const points = geometryToPoints(previewQuery.data.geometry);
    if (!points) {
      setTerrainError("Contour cadastral introuvable - impossible d'enregistrer ce terrain.");
      return;
    }
    const nom = saveName.trim() || previewQuery.data.parcel_id || "Ma parcelle";
    setSavingTerrain(true);
    setTerrainError(null);
    try {
      const created = await addTerrain(token, {
        nom,
        points,
        superficie_ha: previewQuery.data.area_ha ?? undefined,
      });
      const me = await fetchMe(token);
      setUser(me);
      setSelectedTerrainId(created.id);
      setSelectionSource("terrain");
      setClickedPoint(null);
      setShowSaveForm(false);
      setSaveName("");
    } catch (err) {
      setTerrainError(err instanceof AuthApiError ? err.message : "Impossible d'enregistrer ce terrain.");
    } finally {
      setSavingTerrain(false);
    }
  }

  async function handleDeleteTerrain(terrainId: string) {
    if (!token) return;
    setDeletingId(terrainId);
    setTerrainError(null);
    try {
      await deleteTerrain(token, terrainId);
      const me = await fetchMe(token);
      setUser(me);
      if (selectedTerrainId === terrainId) {
        setSelectedTerrainId(me.terrains[0]?.id);
        setSelectionSource(me.terrains[0] ? "terrain" : "carte");
      }
    } catch (err) {
      setTerrainError(err instanceof AuthApiError ? err.message : "Impossible de supprimer ce terrain.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <AppShell>
      <PageHeader
        icon={Sprout}
        tone="harvest"
        title="Conseiller Agricole"
        subtitle="Cliquez une parcelle sur la carte, enregistrez-la, puis lancez l'analyse."
      />

      <Reveal from="up" delay={100} className="card-soft p-5 md:p-6 mt-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-1 min-w-0">
            <Select value={selectValue} onValueChange={handleSelectTerrain}>
              <SelectTrigger className="sm:w-72 rounded-xl h-11">
                <SelectValue placeholder="Choisir un terrain" />
              </SelectTrigger>
              <SelectContent className="z-[1100]" position="popper">
                {terrains.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.nom ?? "Terrain"} ({t.superficie_ha.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha)
                  </SelectItem>
                ))}
                <SelectItem value={EXPLORE_VALUE}>Explorer sur la carte</SelectItem>
              </SelectContent>
            </Select>
            {selectionSource === "terrain" && selectedTerrain && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="rounded-xl text-muted-foreground hover:text-destructive"
                disabled={deletingId === selectedTerrain.id}
                onClick={() => void handleDeleteTerrain(selectedTerrain.id)}
              >
                {deletingId === selectedTerrain.id ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-1.5" />
                )}
                Supprimer
              </Button>
            )}
          </div>
          <div className="lg:text-right max-w-sm">
            <div className="text-sm font-semibold">
              {selectionSource === "terrain" && selectedTerrain
                ? `Terrain « ${selectedTerrain.nom ?? "Terrain"} »`
                : "Cliquez sur votre parcelle"}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {selectionSource === "terrain" && selectedTerrain
                ? "Cliquez ailleurs pour explorer une autre parcelle."
                : "Cliquez sur une parcelle pour afficher son contour et ses voisins."}
            </p>
          </div>
        </div>

        {terrainError && (
          <AlertBanner tone="danger" title="Terrains">
            {terrainError}
          </AlertBanner>
        )}

        <MapPicker
          mode="point"
          onPoint={handleMapPoint}
          markerPosition={selectionSource === "carte" ? clickedPoint : terrainCentroid}
          overlayGeometry={overlayGeometry}
          neighborGeometries={neighborGeometries}
          center={mapCenter}
          zoom={mapZoom}
          height={440}
          showHint={false}
        />

        {activePoint && (
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
            {(previewQuery.data || (selectionSource === "terrain" && selectedTerrain)) && (
              <>
                <div className="grid gap-4 lg:grid-cols-2">
                  {previewQuery.data ? (
                    <ParcelInfoCard
                      parcel={previewQuery.data}
                      overrideAreaHa={
                        selectionSource === "terrain" ? selectedTerrain?.superficie_ha ?? null : null
                      }
                      overrideLabel={
                        selectionSource === "terrain" ? selectedTerrain?.nom ?? null : null
                      }
                    />
                  ) : (
                    <div className="card-soft p-5 space-y-3">
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-16 w-full" />
                    </div>
                  )}
                  {neighborsQuery.isPending ? (
                    <div className="card-soft p-5 space-y-3">
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-16 w-full" />
                    </div>
                  ) : neighborsQuery.data ? (
                    <NeighborsPreviewCard neighbors={neighborsQuery.data} radiusM={NEIGHBORS_RADIUS_M} />
                  ) : null}
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:justify-end">
                  {canSaveExplored && !showSaveForm && (
                    <Button
                      type="button"
                      variant="outline"
                      className="rounded-xl"
                      onClick={() => {
                        setShowSaveForm(true);
                        setSaveName(
                          previewQuery.data?.crop_declared
                            ? `Parcelle ${previewQuery.data.crop_declared}`
                            : previewQuery.data?.parcel_id
                              ? `Réf. ${previewQuery.data.parcel_id}`
                              : "",
                        );
                      }}
                    >
                      <BookmarkPlus className="h-4 w-4 mr-2" />
                      Enregistrer comme mon terrain
                    </Button>
                  )}
                  <Button
                    className="rounded-xl"
                    disabled={analyzeMutation.isPending}
                    onClick={handleAnalyze}
                  >
                    {analyzeMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Sprout className="h-4 w-4 mr-2" />
                    )}
                    {selectionSource === "terrain" && selectedTerrain
                      ? `Analyser ${selectedTerrain.nom ?? "ce terrain"}`
                      : "Analyser cette parcelle"}
                  </Button>
                </div>

                {showSaveForm && canSaveExplored && (
                  <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 flex flex-col sm:flex-row gap-3 sm:items-end">
                    <div className="flex-1 min-w-0">
                      <label htmlFor="save-terrain-nom" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Nom du terrain
                      </label>
                      <Input
                        id="save-terrain-nom"
                        value={saveName}
                        onChange={(e) => setSaveName(e.target.value)}
                        placeholder="ex. Parcelle Nord"
                        className="mt-1.5 h-11 rounded-xl"
                        autoFocus
                      />
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button
                        type="button"
                        variant="ghost"
                        className="rounded-xl"
                        onClick={() => {
                          setShowSaveForm(false);
                          setSaveName("");
                        }}
                      >
                        Annuler
                      </Button>
                      <Button
                        type="button"
                        className="rounded-xl"
                        disabled={savingTerrain}
                        onClick={() => void handleSaveTerrain()}
                      >
                        {savingTerrain ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <BookmarkPlus className="h-4 w-4 mr-2" />}
                        Enregistrer
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Reveal>

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
            <Reveal key={i} from="up" delay={i * 100} className="card-soft p-6 space-y-4">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </Reveal>
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

          <div className="mt-8">
            <WeatherCard weather={analysis.weather} />
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-3">
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
              <div className="flex flex-wrap gap-2 shrink-0">
                {analysis.report && (
                  <Button
                    variant="outline"
                    className="rounded-xl"
                    onClick={() => setShowReport((v) => !v)}
                  >
                    {showReport ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                    {showReport ? "Masquer le rapport" : "Afficher le rapport"}
                    {showReport ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
                  </Button>
                )}
                {analysis.terrain_id && (
                  <Button
                    variant="outline"
                    className="rounded-xl"
                    onClick={() => navigate({ to: "/business" })}
                  >
                    <TrendingUp className="h-4 w-4 mr-2" /> Utiliser dans Conseiller Business
                  </Button>
                )}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {analysis.crop_recommendations.map((c) => (
                <CropCard key={c.culture} crop={c} onDetails={() => setOpenCrop(c)} />
              ))}
            </div>
          </div>

          {showReport && analysis.report && (
            <div className="mt-8 card-soft p-6 md:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="h-11 w-11 rounded-2xl bg-primary/15 text-primary flex items-center justify-center shrink-0">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="font-display text-xl font-semibold">
                    Rapport
                    {(analysis.report.parcel_id ?? analysis.parcel.parcel_id) &&
                      ` - Réf. ${analysis.report.parcel_id ?? analysis.parcel.parcel_id}`}
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

/** WMO weather interpretation codes → Lucide icon (Open-Meteo). */
function weatherIcon(code: number | null | undefined) {
  if (code === null || code === undefined) return Cloud;
  if (code === 0) return Sun;
  if (code <= 2) return CloudSun;
  if (code <= 3) return Cloud;
  if (code <= 48) return CloudFog;
  if (code <= 67 || (code >= 80 && code <= 82)) return CloudRain;
  if (code <= 77 || code === 85 || code === 86) return Snowflake;
  if (code >= 95) return CloudLightning;
  return Cloud;
}

function formatClock(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    // Open-Meteo sometimes returns "HH:MM" already, or date without Z
    const m = iso.match(/T(\d{2}):(\d{2})/);
    if (m) return `${m[1]}h${m[2]}`;
    return iso;
  }
  return `${String(d.getHours()).padStart(2, "0")}h${String(d.getMinutes()).padStart(2, "0")}`;
}

function WeatherCard({ weather }: { weather: WeatherData }) {
  if (weather.source === "unavailable") {
    return (
      <div className="card-soft p-6">
        <p className="text-sm text-muted-foreground">{weather.warning ?? "Météo indisponible pour cette parcelle."}</p>
      </div>
    );
  }

  const Icon = weatherIcon(weather.weather_code);
  const now = new Date();
  const dateLabel = now.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  const timeLabel = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  const updatedLabel = weather.observed_at
    ? `Prévision actualisée à ${formatClock(weather.observed_at).replace("h", "h")}`
    : "Prévision Open-Meteo";

  const temp =
    weather.current_temp_c !== null && weather.current_temp_c !== undefined
      ? Math.round(weather.current_temp_c)
      : weather.daily_temp_mean_c?.[0] != null
        ? Math.round(weather.daily_temp_mean_c[0])
        : null;

  const precip =
    weather.current_precip_mm ??
    (weather.daily_precip_mm?.[0] != null ? weather.daily_precip_mm[0] : null);

  const metrics: { icon: typeof Droplets; value: string }[] = [
    {
      icon: CloudRain,
      value: precip !== null && precip !== undefined ? `${Math.round(precip)}mm` : "-",
    },
    {
      icon: Wind,
      value:
        weather.current_wind_kmh !== null && weather.current_wind_kmh !== undefined
          ? `${Math.round(weather.current_wind_kmh)}km/h`
          : "-",
    },
    {
      icon: Droplet,
      value:
        weather.current_humidity_pct !== null && weather.current_humidity_pct !== undefined
          ? `${Math.round(weather.current_humidity_pct)}%`
          : "-",
    },
    { icon: Sunrise, value: formatClock(weather.sunrise) },
    { icon: Sunset, value: formatClock(weather.sunset) },
    {
      icon: Thermometer,
      value:
        weather.today_temp_min_c != null && weather.today_temp_max_c != null
          ? `${Math.round(weather.today_temp_min_c)}°c/${Math.round(weather.today_temp_max_c)}°c`
          : "-",
    },
  ];

  return (
    <div className="card-soft p-6 md:p-8">
      <div className="text-sm text-muted-foreground">
        {dateLabel} <span className="font-semibold text-foreground">{timeLabel}</span>
      </div>

      <div className="mt-5 flex items-center gap-6 flex-wrap">
        <div
          className="h-20 w-20 md:h-24 md:w-24 rounded-2xl flex items-center justify-center shrink-0"
          style={{ background: "oklch(0.93 0.04 210)", color: "oklch(0.48 0.1 210)" }}
        >
          <Icon className="h-12 w-12 md:h-14 md:w-14" strokeWidth={1.5} />
        </div>
        <div className="font-display text-6xl md:text-7xl font-semibold tracking-tight leading-none">
          {temp !== null ? `${temp}°c` : "-"}
        </div>
        <div className="text-sm text-muted-foreground md:ml-auto">{updatedLabel}</div>
      </div>

      <div className="mt-8 grid grid-cols-3 sm:grid-cols-6 gap-4">
        {metrics.map((m, i) => (
          <div key={i} className="flex flex-col items-center gap-2 text-center">
            <m.icon className="h-6 w-6 text-foreground/80" strokeWidth={1.5} />
            <span className="text-sm font-semibold">{m.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SoilCard({ soil }: { soil: SoilData }) {
  const rows: { label: string; value: ReactNode }[] = [];
  if (soil.ph !== null) rows.push({ label: "pH", value: `${soil.ph.toFixed(1)} - ${phQualifier(soil.ph)}` });
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
              {label} - NDVI {ndvi.toFixed(2)}
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
              Fenêtre d'observation : {vegetation.observation_window_days} jours ({vegetation.valid_pixel_count ?? 0} pixels valides) - Sentinel-2.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function ParcelInfoCard({
  parcel,
  overrideAreaHa = null,
  overrideLabel = null,
}: {
  parcel: ParcelResolution;
  /** Surface du terrain déclaré (prioritaire sur la surface cadastrale au centroïde). */
  overrideAreaHa?: number | null;
  overrideLabel?: string | null;
}) {
  if (!parcel.resolved && overrideAreaHa === null) {
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
  const sourceLabel = overrideLabel
    ? `Mon terrain - ${overrideLabel}`
    : parcel.source === "cadastre"
      ? "Cadastre (IGN)"
      : parcel.source === "rpg"
        ? "RPG"
        : "Tracé manuel";
  const areaHa = overrideAreaHa ?? parcel.area_ha;

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
          value={areaHa !== null && areaHa !== undefined ? `${areaHa.toFixed(2)} ha` : "Inconnue"}
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
        Cultures voisines - {neighbors.neighbor_count} parcelle{neighbors.neighbor_count > 1 ? "s" : ""} ({radiusM} m)
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
        Fertilisation & irrigation - {displayCrop(cropCode)}
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
