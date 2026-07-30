import { createFileRoute, Link, useParams } from "@tanstack/react-router";
import { listings } from "@/features/marketplace/data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MapPin, Phone, Mail, Sparkles } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/marketplace/$id")({
  component: Detail,
});

function Detail() {
  const { id } = useParams({ from: "/marketplace/$id" });
  const l = listings.find((x) => x.id === id);
  const [revealed, setRevealed] = useState(false);

  if (!l) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Annonce introuvable.</p>
        <Link to="/marketplace" className="text-primary underline mt-3 inline-block">Retour au marketplace</Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <Link to="/marketplace" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Retour aux annonces
      </Link>

      <div className="mt-4 grid gap-6 md:grid-cols-[1fr_320px]">
        <div>
          <div
            className={
              l.kind === "recolte"
                ? "aspect-[4/3] rounded-3xl bg-harvest/10 flex items-center justify-center text-9xl"
                : "aspect-[4/3] rounded-3xl bg-waste/15 flex items-center justify-center text-9xl"
            }
          >
            <span aria-hidden>{l.emoji}</span>
          </div>

          <div className="mt-6 flex items-center gap-2">
            {l.kind === "recolte" ? (
              <Badge className="border border-harvest/30 bg-harvest/15 text-harvest">Récolte</Badge>
            ) : (
              <Badge className="border border-waste/40 bg-waste/20 text-waste-foreground">Déchet valorisable</Badge>
            )}
            <span className="text-sm text-muted-foreground inline-flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" /> {l.region} · {l.distance}
            </span>
          </div>

          <h1 className="mt-2 font-display text-3xl md:text-4xl font-semibold">{l.title}</h1>
          <div className="mt-2 text-muted-foreground">{l.quantity}</div>

          <p className="mt-6 text-base leading-relaxed">{l.description}</p>

          {l.utility && (
            <div className="mt-6 rounded-2xl bg-waste/10 border border-waste/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-waste-foreground">
                <Sparkles className="h-4 w-4" /> Peut servir à
              </div>
              <p className="mt-1 text-sm">{l.utility}</p>
            </div>
          )}
        </div>

        {/* Contact panel */}
        <aside className="card-soft p-6 h-fit md:sticky md:top-6">
          <div className="text-xs text-muted-foreground">Prix</div>
          <div className="font-display text-3xl font-semibold text-primary">{l.price}</div>

          {!revealed ? (
            <Button className="w-full mt-6 rounded-xl h-12" onClick={() => setRevealed(true)}>
              Contacter le vendeur
            </Button>
          ) : (
            <div className="mt-6 space-y-3">
              <a href={`tel:${l.contact.phone}`} className="flex items-center gap-3 rounded-xl bg-secondary p-3">
                <Phone className="h-5 w-5 text-primary" />
                <div>
                  <div className="text-xs text-muted-foreground">Téléphone</div>
                  <div className="font-medium">{l.contact.phone}</div>
                </div>
              </a>
              <a href={`mailto:${l.contact.email}`} className="flex items-center gap-3 rounded-xl bg-secondary p-3">
                <Mail className="h-5 w-5 text-primary" />
                <div className="min-w-0">
                  <div className="text-xs text-muted-foreground">Email</div>
                  <div className="font-medium truncate">{l.contact.email}</div>
                </div>
              </a>
            </div>
          )}

          <p className="text-xs text-muted-foreground mt-4">
            Aucune commission — vous discutez directement avec l'agriculteur.
          </p>
        </aside>
      </div>
    </div>
  );
}
