/**
 * Affiche, pour les cultures recommandées par l'agent Agriculture,
 * les déchets produits et leurs voies de valorisation (agent Déchets).
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Recycle, ChevronRight, ChevronDown, ChevronUp, Loader2, ArrowRight, Leaf } from "lucide-react";
import { AlertBanner } from "@/components/AlertBanner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cultureLabel } from "@/lib/cropRecommendations";
import {
  fetchMarketplaceWasteSuggestions,
  fetchWasteProfilesForCrops,
  WasteApiError,
  type CropWasteProfile,
  type WasteOut,
} from "@/lib/wasteApi";
import { cn } from "@/lib/utils";

type Props = {
  cultures: string[];
  /** When set, highlight this crop (e.g. after business decision). */
  highlightCulture?: string | null;
  className?: string;
};

function ChainLine({ waste }: { waste: WasteOut }) {
  if (waste.transformations.length > 0) {
    return (
      <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
        {waste.transformations.map((t, i) => (
          <span key={`${t.process}-${t.output_product}-${i}`}>
            {i > 0 ? " · " : null}
            <span className="text-foreground/80">{t.process_label}</span>
            {" → "}
            <span className="font-medium text-foreground">{t.output_label}</span>
          </span>
        ))}
      </p>
    );
  }
  if (waste.final_products_labels.length > 0) {
    return (
      <p className="text-sm text-muted-foreground mt-1.5">
        Produits : {waste.final_products_labels.slice(0, 4).join(" · ")}
      </p>
    );
  }
  return null;
}

function WasteRow({ waste, culture }: { waste: WasteOut; culture: string }) {
  return (
    <div className="rounded-2xl bg-secondary/40 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium">{waste.name_label}</div>
          {waste.composition_summary[0] && (
            <div className="text-xs text-muted-foreground mt-0.5">{waste.composition_summary[0]}</div>
          )}
          <ChainLine waste={waste} />
        </div>
        <Link
          to="/marketplace/nouveau"
          search={{
            kind: "dechet",
            culture,
            waste: waste.name_label,
            title: waste.marketplace_title,
            utility: waste.marketplace_utility,
            description: waste.marketplace_description,
          }}
          className="shrink-0 text-xs font-medium text-primary inline-flex items-center gap-1 hover:underline"
        >
          Déposer
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}

function ProfileCard({
  profile,
  highlighted,
}: {
  profile: CropWasteProfile;
  highlighted: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const label = profile.crop_label_fr || cultureLabel(profile.culture);
  const wastes = profile.wastes.slice(0, 4);
  const canExpand = profile.found && wastes.length > 0;

  return (
    <div
      className={cn(
        "card-soft p-5 flex flex-col",
        highlighted && "ring-2 ring-primary/30 border-primary/40",
      )}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="h-9 w-9 rounded-xl bg-waste/20 text-waste-foreground flex items-center justify-center shrink-0">
          <Recycle className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="font-display text-lg font-semibold truncate">{label}</div>
          {profile.scientific_name && (
            <div className="text-xs text-muted-foreground italic truncate">{profile.scientific_name}</div>
          )}
        </div>
      </div>

      {!profile.found ? (
        <p className="text-sm text-muted-foreground">{profile.message || "Pas encore de données."}</p>
      ) : (
        <>
          <div
            className={cn(
              "space-y-2 flex-1 relative",
              !expanded && canExpand && "max-h-32 overflow-hidden",
            )}
          >
            {wastes.map((w) => (
              <WasteRow key={w.id} waste={w} culture={profile.culture} />
            ))}
            {!expanded && canExpand && (
              <div
                className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-card to-transparent"
                aria-hidden
              />
            )}
          </div>
          {canExpand && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2 w-full rounded-xl text-xs font-medium text-muted-foreground hover:text-foreground"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? (
                <>
                  Réduire
                  <ChevronUp className="h-3.5 w-3.5 ml-1" />
                </>
              ) : (
                <>
                  Voir plus
                  <ChevronDown className="h-3.5 w-3.5 ml-1" />
                </>
              )}
            </Button>
          )}
        </>
      )}
    </div>
  );
}

export function CropWasteValorization({ cultures, highlightCulture, className }: Props) {
  const query = useQuery({
    queryKey: ["waste-for-crops", [...cultures].sort().join("|")],
    queryFn: () => fetchWasteProfilesForCrops(cultures),
    enabled: cultures.length > 0,
    staleTime: 5 * 60_000,
    retry: 1,
  });

  if (cultures.length === 0) return null;

  return (
    <section className={cn("mt-10", className)}>
      <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest uppercase text-waste-foreground">
            <Leaf className="h-3.5 w-3.5" />
            Économie circulaire
          </div>
          <h2 className="font-display text-3xl font-semibold mt-1">Déchets &amp; valorisation</h2>
          <p className="text-muted-foreground mt-1 max-w-2xl">
            Pour chaque culture recommandée : quels résidus après récolte, et en quoi ils peuvent se
            transformer — prêts à être déposés sur la marketplace.
          </p>
        </div>
      </div>

      {query.isPending && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cultures.slice(0, 3).map((c) => (
            <Skeleton key={c} className="h-36 rounded-3xl" />
          ))}
        </div>
      )}

      {query.isError && (
        <AlertBanner
          tone="warning"
          title="Agent Déchets indisponible"
        >
          {query.error instanceof WasteApiError
            ? query.error.message
            : "Impossible de charger les profils de valorisation."}
        </AlertBanner>
      )}

      {query.data && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {query.data.profiles.map((p) => (
              <ProfileCard
                key={p.culture}
                profile={p}
                highlighted={Boolean(highlightCulture && highlightCulture === p.culture)}
              />
            ))}
          </div>
          {query.isFetching && (
            <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Mise à jour…
            </div>
          )}
        </>
      )}
    </section>
  );
}

type MarketplaceBlockProps = {
  culture: string;
  className?: string;
};

/** Post-decision block: wastes to list on the marketplace for the chosen crop. */
export function MarketplaceWasteSuggestions({ culture, className }: MarketplaceBlockProps) {
  const query = useQuery({
    queryKey: ["waste-marketplace", culture],
    queryFn: () => fetchMarketplaceWasteSuggestions(culture),
    enabled: Boolean(culture),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  if (!culture) return null;

  return (
    <section className={cn("mt-8 max-w-2xl mx-auto text-left", className)}>
      <div className="card-soft p-6 md:p-8">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-2xl bg-waste/20 text-waste-foreground flex items-center justify-center shrink-0">
            <Recycle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold">Après la récolte</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {query.data?.harvest_hint ||
                `Déposez les sous-produits de ${cultureLabel(culture)} sur la marketplace.`}
            </p>
          </div>
        </div>

        {query.isPending && (
          <div className="mt-5 space-y-2">
            <Skeleton className="h-16 rounded-2xl" />
            <Skeleton className="h-16 rounded-2xl" />
          </div>
        )}

        {query.isError && (
          <p className="mt-4 text-sm text-muted-foreground">
            {query.error instanceof WasteApiError
              ? query.error.message
              : "Suggestions indisponibles pour le moment."}
          </p>
        )}

        {query.data?.found && query.data.suggestions.length > 0 && (
          <div className="mt-5 space-y-3">
            {query.data.suggestions.map((w) => (
              <div
                key={w.id}
                className="rounded-2xl border border-border bg-card/60 p-4 flex flex-col sm:flex-row sm:items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{w.name_label}</div>
                  <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{w.marketplace_utility}</p>
                </div>
                <Button asChild className="rounded-xl shrink-0" size="sm">
                  <Link
                    to="/marketplace/nouveau"
                    search={{
                      kind: "dechet",
                      culture,
                      waste: w.name_label,
                      title: w.marketplace_title,
                      utility: w.marketplace_utility,
                      description: w.marketplace_description,
                    }}
                  >
                    Créer l&apos;annonce
                    <ArrowRight className="h-4 w-4 ml-1" />
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        )}

        {query.data && !query.data.found && (
          <p className="mt-4 text-sm text-muted-foreground">{query.data.message}</p>
        )}
      </div>
    </section>
  );
}
