import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/marketplace/nouveau")({
  component: NewListing,
});

const kinds = [
  { id: "recolte", label: "Récolte", emoji: "🌾", desc: "Vendez votre production" },
  { id: "dechet", label: "Déchet valorisable", emoji: "♻️", desc: "Donnez ou revendez une matière réutilisable" },
] as const;

function NewListing() {
  const nav = useNavigate();
  const [kind, setKind] = useState<(typeof kinds)[number]["id"]>("recolte");
  const [crop, setCrop] = useState("Blé tendre");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [desc, setDesc] = useState("");
  const [utility, setUtility] = useState("");
  const [aiFilled, setAiFilled] = useState(false);

  const fillWithAI = () => {
    if (kind === "recolte") {
      setQuantity((q) => q || "2,5 tonnes");
      setPrice((p) => p || "285 €/t");
      setDesc((d) => d || `Récolte 2026 de ${crop.toLowerCase()}, qualité standard, disponible sur place. Livraison possible dans un rayon de 30 km.`);
    } else {
      setQuantity((q) => q || "100 bottes");
      setPrice((p) => p || "À convenir");
      setDesc((d) => d || `Sous-produit de la culture ${crop.toLowerCase()}, stocké à l'abri, à récupérer sur place.`);
      setUtility((u) => u || "Peut servir de paillage, de litière animale, ou pour la méthanisation.");
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
      <div>
        <Label className="text-sm mb-3 block">Type d'annonce</Label>
        <div className="grid gap-3 sm:grid-cols-2">
          {kinds.map((k) => (
            <button
              key={k.id}
              type="button"
              onClick={() => setKind(k.id)}
              className={cn(
                "text-left rounded-2xl border p-4 transition-all",
                kind === k.id ? "border-primary bg-primary/5 ring-2 ring-primary/20" : "border-border bg-card hover:border-primary/40",
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
            <div className="font-semibold">Laissez l'IA préparer votre annonce</div>
            <p className="text-sm text-muted-foreground mt-1">
              Nous pré-remplissons quantité, prix suggéré et description - vous n'avez plus qu'à ajuster.
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
          <Input id="qty" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Ex : 3 tonnes" className="mt-2 h-12 rounded-xl" />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="price">Prix {kind === "dechet" && <span className="text-muted-foreground text-xs">(ou &laquo; gratuit &raquo; / &laquo; à convenir &raquo;)</span>}</Label>
          <Input id="price" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Ex : 285 €/t" className="mt-2 h-12 rounded-xl" />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="desc">Description</Label>
          <Textarea id="desc" value={desc} onChange={(e) => setDesc(e.target.value)} rows={4} className="mt-2 rounded-xl" />
        </div>
        {kind === "dechet" && (
          <div className="sm:col-span-2">
            <Label htmlFor="util">À quoi ça peut servir ?</Label>
            <Textarea id="util" value={utility} onChange={(e) => setUtility(e.target.value)} rows={3} className="mt-2 rounded-xl" />
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <Button type="button" variant="outline" onClick={() => nav({ to: "/marketplace" })} className="rounded-xl h-12">
          Annuler
        </Button>
        <Button type="submit" className="rounded-xl h-12 px-8">
          Publier l'annonce
        </Button>
      </div>
    </form>
  );
}
