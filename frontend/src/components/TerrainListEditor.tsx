import { useState } from "react";
import { MapPin, Plus, Ruler, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MapPicker } from "@/components/MapPicker";
import { areaHectares, type LatLng } from "@/lib/terrain";

export type DraftTerrain = {
  /** Identifiant local (pas encore persisté) ou id réel renvoyé par le backend. */
  id: string;
  nom: string;
  points: LatLng[];
};

/**
 * Gère une liste de terrains (nom de zone + contour tracé sur la carte).
 * Réutilisé depuis la page Agriculture et la page Profil.
 */
export function TerrainListEditor({
  terrains,
  onChange,
}: {
  terrains: DraftTerrain[];
  onChange: (terrains: DraftTerrain[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [draftNom, setDraftNom] = useState("");
  const [draftPoints, setDraftPoints] = useState<LatLng[]>([]);

  function startAdd() {
    setDraftNom("");
    setDraftPoints([]);
    setAdding(true);
  }

  function cancelAdd() {
    setAdding(false);
  }

  function confirmAdd() {
    if (draftPoints.length < 3 || !draftNom.trim()) return;
    onChange([...terrains, { id: crypto.randomUUID(), nom: draftNom.trim(), points: draftPoints }]);
    setAdding(false);
  }

  function remove(id: string) {
    onChange(terrains.filter((t) => t.id !== id));
  }

  return (
    <div className="space-y-4">
      {terrains.map((t) => (
        <div key={t.id} className="card-soft p-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="font-semibold flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary shrink-0" /> {t.nom}
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <Ruler className="h-3 w-3" />{" "}
              {areaHectares(t.points).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha ·{" "}
              {t.points.length} points GPS
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0 text-muted-foreground hover:text-destructive"
            onClick={() => remove(t.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}

      {adding ? (
        <div className="card-soft p-4 space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="terrain-nom">Nom de la zone</Label>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={cancelAdd}
              className="h-7 w-7"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <Input
            id="terrain-nom"
            value={draftNom}
            onChange={(e) => setDraftNom(e.target.value)}
            placeholder="ex. Parcelle Nord, Champ de la Rivière..."
            className="h-11 rounded-xl"
          />
          <MapPicker onPolygon={setDraftPoints} height={360} />
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {draftPoints.length < 3
                ? `Placez ${3 - draftPoints.length} point${3 - draftPoints.length > 1 ? "s" : ""} de plus`
                : `${areaHectares(draftPoints).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha`}
            </span>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={cancelAdd} className="rounded-xl">
              Annuler
            </Button>
            <Button
              type="button"
              disabled={draftPoints.length < 3 || !draftNom.trim()}
              onClick={confirmAdd}
              className="rounded-xl"
            >
              Ajouter ce terrain
            </Button>
          </div>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          onClick={startAdd}
          className="rounded-xl h-12 w-full"
        >
          <Plus className="h-4 w-4 mr-2" /> Ajouter un terrain
        </Button>
      )}
    </div>
  );
}
