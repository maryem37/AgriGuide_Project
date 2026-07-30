import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowRight, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MapPicker } from "@/components/MapPicker";
import { saveTerrain } from "@/lib/terrain";

export const Route = createFileRoute("/onboarding/terrain")({
  head: () => ({
    meta: [
      { title: "Choisir mon terrain — AgriGuide" },
      { name: "description", content: "Tracez votre parcelle sur la carte pour recevoir des conseils personnalisés." },
      { property: "og:title", content: "Choisir mon terrain — AgriGuide" },
      { property: "og:description", content: "Sélectionnez votre parcelle en quelques touches." },
    ],
  }),
  component: Page,
});

function Page() {
  const navigate = useNavigate();
  const [points, setPoints] = useState<[number, number][]>([]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6 md:py-10">
        <div className="flex items-start md:items-center gap-3 mb-6 md:mb-8 flex-col md:flex-row md:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-primary">
              <MapPin className="h-4 w-4" /> Étape 1 sur 1
            </div>
            <h1 className="mt-2 font-display text-3xl md:text-4xl font-semibold">Où se trouve votre exploitation ?</h1>
            <p className="mt-1 text-muted-foreground max-w-2xl">
              Tracez le contour de votre parcelle. Nous utilisons ces informations pour analyser votre sol,
              la météo locale et les cultures adaptées.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 rounded-2xl bg-secondary px-4 py-2 text-sm">
            <div className="h-2 w-2 rounded-full bg-primary" />
            {points.length === 0
              ? "Aucun point"
              : points.length < 3
              ? `${points.length} point${points.length > 1 ? "s" : ""} — placez ${3 - points.length} de plus`
              : `Parcelle définie (${points.length} points)`}
          </div>
        </div>

        <MapPicker onPolygon={setPoints} height={520} />

        <div className="mt-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            Vous pourrez ajuster votre terrain à tout moment depuis votre profil.
          </p>
          <Button
            size="lg"
            disabled={points.length < 3}
            onClick={() => {
              saveTerrain(points);
              navigate({ to: "/dashboard" });
            }}
            className="h-14 px-8 rounded-2xl text-base"
          >
            Continuer <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
