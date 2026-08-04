import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { listings } from "@/features/marketplace/data";
import { ListingCard } from "@/features/marketplace/ListingCard";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PackageOpen, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/marketplace/")({
  component: Browse,
});

const kinds = [
  { id: "all", label: "Tout" },
  { id: "recolte", label: "Récoltes" },
  { id: "dechet", label: "Déchets valorisables" },
] as const;

function Browse() {
  const [kind, setKind] = useState<(typeof kinds)[number]["id"]>("all");
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("all");
  const [price, setPrice] = useState("all");

  const regions = useMemo(() => Array.from(new Set(listings.map((l) => l.region))), []);

  const filtered = useMemo(
    () =>
      listings.filter((l) => {
        if (kind !== "all" && l.kind !== kind) return false;
        if (q && !l.title.toLowerCase().includes(q.toLowerCase())) return false;
        if (region !== "all" && l.region !== region) return false;
        if (price === "free" && !l.freePrice) return false;
        if (price === "paid" && l.freePrice) return false;
        return true;
      }),
    [kind, q, region, price],
  );

  return (
    <div>
      {/* Kind pills */}
      <div className="flex gap-2 mb-5">
        {kinds.map((k, i) => (
          <button
            key={k.id}
            onClick={() => setKind(k.id)}
            style={{ animationDelay: `${i * 70}ms` }}
            className={cn(
              "page-enter press rounded-full border px-4 py-2 text-sm font-medium transition-all duration-300",
              kind === k.id
                ? "bg-primary text-primary-foreground border-primary shadow-soft"
                : "bg-card border-border hover:bg-secondary hover:-translate-y-0.5",
            )}
          >
            {k.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="card-soft p-4 mb-6 grid gap-3 md:grid-cols-[1fr_200px_200px]">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher (blé, colza, paille...)"
            className="pl-9 h-11 rounded-xl"
          />
        </div>
        <Select value={region} onValueChange={setRegion}>
          <SelectTrigger className="h-11 rounded-xl">
            <SelectValue placeholder="Région" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes les régions</SelectItem>
            {regions.map((r) => (
              <SelectItem key={r} value={r}>
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={price} onValueChange={setPrice}>
          <SelectTrigger className="h-11 rounded-xl">
            <SelectValue placeholder="Prix" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les prix</SelectItem>
            <SelectItem value="free">Gratuit / à convenir</SelectItem>
            <SelectItem value="paid">Avec prix</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <div className="page-enter flex flex-col items-center gap-3 py-20 text-center text-muted-foreground">
          <PackageOpen className="float-soft h-10 w-10 opacity-40" />
          Aucune annonce ne correspond à vos filtres.
        </div>
      ) : (
        // La clé dépend des filtres pour rejouer l'entrée en cascade à chaque tri.
        <div
          key={`${kind}-${region}-${price}-${q}`}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {filtered.map((l, i) => (
            <ListingCard key={l.id} l={l} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
