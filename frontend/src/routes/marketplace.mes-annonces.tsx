import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { listings as initial } from "@/features/marketplace/data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, MapPin } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";

export const Route = createFileRoute("/marketplace/mes-annonces")({
  component: Mine,
});

const statusStyle: Record<string, string> = {
  disponible: "bg-harvest/15 text-harvest border-harvest/30",
  reserve: "bg-waste/20 text-waste-foreground border-waste/40",
  expire: "bg-muted text-muted-foreground border-border",
};
const statusLabel: Record<string, string> = {
  disponible: "Disponible",
  reserve: "Réservé",
  expire: "Expiré",
};

function Mine() {
  const [items, setItems] = useState(initial.filter((l) => l.mine));

  const reserve = (id: string) => {
    setItems((it) => it.map((l) => (l.id === id ? { ...l, status: "reserve" } : l)));
    toast.success("Annonce marquée comme réservée");
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Vous n'avez pas encore d'annonce active.</p>
        <Button asChild className="mt-4 rounded-xl">
          <Link to="/marketplace/nouveau">Déposer ma première annonce</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((l) => (
        <div key={l.id} className="card-soft p-4 flex flex-col sm:flex-row gap-4">
          <div
            className={
              l.kind === "recolte"
                ? "sm:w-32 aspect-square rounded-2xl bg-harvest/10 flex items-center justify-center text-5xl shrink-0"
                : "sm:w-32 aspect-square rounded-2xl bg-waste/15 flex items-center justify-center text-5xl shrink-0"
            }
          >
            <span aria-hidden>{l.emoji}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {l.kind === "recolte" ? (
                <Badge className="border border-harvest/30 bg-harvest/15 text-harvest">Récolte</Badge>
              ) : (
                <Badge className="border border-waste/40 bg-waste/20 text-waste-foreground">Déchet valorisable</Badge>
              )}
              <Badge className={`border ${statusStyle[l.status ?? "disponible"]}`}>
                {statusLabel[l.status ?? "disponible"]}
              </Badge>
              <span className="text-xs text-muted-foreground inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" /> {l.region}
              </span>
            </div>
            <div className="mt-1 font-display text-lg font-semibold">{l.title}</div>
            <div className="text-sm text-muted-foreground">{l.quantity} · {l.price}</div>
          </div>
          <div className="flex sm:flex-col gap-2 sm:items-end sm:justify-center">
            <Button asChild variant="outline" size="sm" className="rounded-xl">
              <Link to="/marketplace/$id" params={{ id: l.id }}>Voir</Link>
            </Button>
            {l.status !== "reserve" && (
              <Button size="sm" className="rounded-xl" onClick={() => reserve(l.id)}>
                <CheckCircle2 className="h-4 w-4 mr-1" /> Marquer réservé
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
