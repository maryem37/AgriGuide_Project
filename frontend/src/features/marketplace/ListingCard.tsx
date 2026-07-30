import { Link } from "@tanstack/react-router";
import { MapPin } from "lucide-react";
import type { Listing } from "@/features/marketplace/data";
import { Badge } from "@/components/ui/badge";

export function ListingCard({ l }: { l: Listing }) {
  return (
    <Link
      to="/marketplace/$id"
      params={{ id: l.id }}
      className="card-soft p-4 flex flex-col hover:card-lift group"
    >
      <div
        className={
          l.kind === "recolte"
            ? "aspect-[4/3] rounded-2xl bg-harvest/10 flex items-center justify-center text-6xl"
            : "aspect-[4/3] rounded-2xl bg-waste/15 flex items-center justify-center text-6xl"
        }
      >
        <span aria-hidden>{l.emoji}</span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        {l.kind === "recolte" ? (
          <Badge className="border border-harvest/30 bg-harvest/15 text-harvest">Récolte</Badge>
        ) : (
          <Badge className="border border-waste/40 bg-waste/20 text-waste-foreground">Déchet valorisable</Badge>
        )}
        <span className="text-xs text-muted-foreground inline-flex items-center gap-1">
          <MapPin className="h-3 w-3" /> {l.region} · {l.distance}
        </span>
      </div>
      <div className="mt-2 font-display text-lg font-semibold leading-tight">{l.title}</div>
      <div className="text-sm text-muted-foreground">{l.quantity}</div>
      <div className="mt-2 font-display text-xl font-semibold text-primary">{l.price}</div>
    </Link>
  );
}
