import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { cultureLabel } from "@/lib/cropRecommendations";

type NouveauSearch = {
  kind?: "recolte" | "dechet";
  culture?: string;
  waste?: string;
  title?: string;
  utility?: string;
  description?: string;
};

export const Route = createFileRoute("/marketplace/nouveau")({
  validateSearch: (search: Record<string, unknown>): NouveauSearch => ({
    kind: search.kind === "dechet" || search.kind === "recolte" ? search.kind : undefined,
    culture: typeof search.culture === "string" ? search.culture : undefined,
    waste: typeof search.waste === "string" ? search.waste : undefined,
    title: typeof search.title === "string" ? search.title : undefined,
    utility: typeof search.utility === "string" ? search.utility : undefined,
    description: typeof search.description === "string" ? search.description : undefined,
  }),
  component: NewListing,
});

const kinds = [
  { id: "recolte", label: "Récolte", emoji: "🌾", desc: "Vendez votre production" },
  { id: "dechet", label: "Déchet valorisable", emoji: "♻️", desc: "Donnez ou revendez une matière réutilisable" },
] as const;

function NewListing() {
  const nav = useNavigate();
  const search = Route.useSearch();

  const [kind, setKind] = useState<(typeof kinds)[number]["id"]>(search.kind ?? "recolte");
  const [crop, setCrop] = useState(() => {
    if (search.waste) return search.waste;
    if (search.title) return search.title;
    if (search.culture) return cultureLabel(search.culture);
    return "Blé tendre";
  });
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [desc, setDesc] = useState(search.description ?? "");
  const [utility, setUtility] = useState(search.utility ?? "");
  const [aiFilled, setAiFilled] = useState(Boolean(search.utility || search.description));

  // Prefill when arriving from agriculture / business waste CTAs
  useEffect(() => {
    if (search.kind) setKind(search.kind);
    if (search.waste) setCrop(search.waste);
    else if (search.title) setCrop(search.title);
    else if (search.culture) setCrop(cultureLabel(search.culture));
    if (search.utility) setUtility(search.utility);
    if (search.description) setDesc(search.description);
    if (search.utility || search.description) setAiFilled(true);
  }, [search.kind, search.waste, search.title, search.culture, search.utility, search.description]);

  const fillWithAI = () => {
    if (kind === "recolte") {
      setQuantity((q) => q || "2,5 tonnes");
      setPrice((p) => p || "285 €/t");
      setDesc(
        (d) =>
          d ||
          `Récolte 2026 de ${crop.toLowerCase()}, qualité standard, disponible sur place. Livraison possible dans un rayon de 30 km.`,
      );
    } else if (search.utility || search.description) {
      // Keep agent-déchets suggestions if present; only fill empty qty/price
      setQuantity((q) => q || "À estimer après récolte");
      setPrice((p) => p || "À convenir");
      if (!desc && search.description) setDesc(search.description);
      if (!utility && search.utility) setUtility(search.utility);
    } else {
      setQuantity((q) => q || "100 bottes");
      setPrice((p) => p || "À convenir");
      setDesc(
        (d) =>
          d ||
          `Sous-produit de la culture ${crop.toLowerCase()}, stocké à l'abri, à récupérer sur place.`,
      );
      setUtility(
        (u) => u || "Peut servir de paillage, de litière animale, ou pour la méthanisation.",
      );
    }
    setAiFilled(true);
    toast.success("Suggestions ajoutées - ajustez à votre convenance.");
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Annonce publiée !");
    nav({ to: "/marketplace/mes-annonces" });
  };

  return (
    <form onSubmit={submit} className="max-w-3xl space-y-6">
      {(search.culture || search.waste) && kind === "dechet" && (
        <div className="rounded-2xl border border-waste/40 bg-waste/10 px-4 py-3 text-sm text-waste-foreground">
          Prérempli par l&apos;agent Déchets
          {search.culture ? ` pour ${cultureLabel(search.culture)}` : ""}.
          Vérifiez quantité et prix avant de publier.
        </div>
      )}

      <div>
        <Label className="text-sm mb-3 block">Type d&apos;annonce</Label>
        <div className="grid gap-3 sm:grid-cols-2">
          {kinds.map((k) => (
            <button
              key={k.id}
              type="button"
              onClick={() => setKind(k.id)}
              className={cn(
                "text-left rounded-2xl border p-4 transition-all",
                kind === k.id
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border bg-card hover:border-primary/40",
              )}
            >
              <div className="text-3xl">{k.emoji}</div>
              <div className="font-display text-lg font-semibold mt-2">{k.label}</div>
              <div className="text-sm text-muted-foreground">{k.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="card-soft p-5 bg-gradient-warm">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 shrink-0 rounded-xl bg-card flex items-center justify-center text-primary">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <div className="font-semibold">Laissez l&apos;IA préparer votre annonce</div>
            <p className="text-sm text-muted-foreground mt-1">
              Nous pré-remplissons quantité, prix suggéré et description - vous n&apos;avez plus qu&apos;à
              ajuster.
            </p>
          </div>
          <Button type="button" onClick={fillWithAI} className="rounded-xl shrink-0" variant="secondary">
            {aiFilled ? <CheckCircle2 className="h-4 w-4 mr-1" /> : <Sparkles className="h-4 w-4 mr-1" />}
            {aiFilled ? "Suggéré" : "Suggérer"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="crop">Culture / matière</Label>
          <Input id="crop" value={crop} onChange={(e) => setCrop(e.target.value)} className="mt-2 h-12 rounded-xl" />
        </div>
        <div>
          <Label htmlFor="qty">Quantité</Label>
          <Input
            id="qty"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="Ex : 3 tonnes"
            className="mt-2 h-12 rounded-xl"
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="price">
            Prix{" "}
            {kind === "dechet" && (
              <span className="text-muted-foreground text-xs">(ou &laquo; gratuit &raquo; / &laquo; à convenir &raquo;)</span>
            )}
          </Label>
          <Input
            id="price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Ex : 285 €/t"
            className="mt-2 h-12 rounded-xl"
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="desc">Description</Label>
          <Textarea id="desc" value={desc} onChange={(e) => setDesc(e.target.value)} rows={4} className="mt-2 rounded-xl" />
        </div>
        {kind === "dechet" && (
          <div className="sm:col-span-2">
            <Label htmlFor="util">À quoi ça peut servir ?</Label>
            <Textarea
              id="util"
              value={utility}
              onChange={(e) => setUtility(e.target.value)}
              rows={3}
              className="mt-2 rounded-xl"
            />
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <Button type="button" variant="outline" onClick={() => nav({ to: "/marketplace" })} className="rounded-xl h-12">
          Annuler
        </Button>
        <Button type="submit" className="rounded-xl h-12 px-8">
          Publier l&apos;annonce
        </Button>
      </div>
    </form>
  );
}
