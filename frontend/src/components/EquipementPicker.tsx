import { useState } from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { EQUIPEMENT_OPTIONS, equipementLabel, slugifyEquipement } from "@/lib/equipements";
import type { EquipementType } from "@/lib/authApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Sélecteur de matériel agricole détenu — cases à cocher visuelles (icône + nom). */
export function EquipementPicker({
  selected,
  onChange,
}: {
  selected: EquipementType[];
  onChange: (value: EquipementType[]) => void;
}) {
  const [showOther, setShowOther] = useState(false);
  const [otherLabel, setOtherLabel] = useState("");
  const [otherError, setOtherError] = useState<string | null>(null);

  const presetValues = new Set(EQUIPEMENT_OPTIONS.map((o) => o.value));
  const customSelected = selected.filter((v) => !presetValues.has(v));

  function toggle(value: EquipementType) {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  }

  function addOther() {
    const slug = slugifyEquipement(otherLabel);
    if (!slug) {
      setOtherError("Indiquez un nom (2–50 caractères, lettres ou chiffres).");
      return;
    }
    if (selected.includes(slug)) {
      setOtherError("Ce matériel est déjà dans la liste.");
      return;
    }
    onChange([...selected, slug]);
    setOtherLabel("");
    setOtherError(null);
    setShowOther(false);
  }

  function removeCustom(value: EquipementType) {
    onChange(selected.filter((v) => v !== value));
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {EQUIPEMENT_OPTIONS.map(({ value, label, icon: Icon }) => {
          const active = selected.includes(value);
          return (
            <button
              key={value}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border p-4 text-center transition-all",
                active
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border bg-card hover:border-primary/40",
              )}
            >
              <div
                className={cn(
                  "h-12 w-12 rounded-xl flex items-center justify-center transition-colors",
                  active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground",
                )}
              >
                <Icon className="h-6 w-6" />
              </div>
              <span className="text-xs font-medium leading-tight">{label}</span>
            </button>
          );
        })}

        <button
          type="button"
          aria-pressed={showOther}
          onClick={() => {
            setShowOther((v) => !v);
            setOtherError(null);
          }}
          className={cn(
            "flex flex-col items-center gap-2 rounded-2xl border p-4 text-center transition-all",
            showOther
              ? "border-primary bg-primary/5 ring-2 ring-primary/20"
              : "border-dashed border-border bg-card hover:border-primary/40",
          )}
        >
          <div
            className={cn(
              "h-12 w-12 rounded-xl flex items-center justify-center transition-colors",
              showOther ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground",
            )}
          >
            <Plus className="h-6 w-6" />
          </div>
          <span className="text-xs font-medium leading-tight">Autres</span>
        </button>
      </div>

      {showOther && (
        <div className="flex flex-col sm:flex-row gap-2 sm:items-start rounded-2xl border border-border bg-muted/30 p-3">
          <div className="flex-1 space-y-1">
            <Input
              value={otherLabel}
              onChange={(e) => {
                setOtherLabel(e.target.value);
                setOtherError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addOther();
                }
              }}
              placeholder="Ex. : épandeur, broyeur…"
              maxLength={50}
              aria-label="Autre matériel"
            />
            {otherError && <p className="text-xs text-destructive">{otherError}</p>}
          </div>
          <Button type="button" onClick={addOther} className="shrink-0">
            Ajouter
          </Button>
        </div>
      )}

      {customSelected.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {customSelected.map((value) => (
            <li
              key={value}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-medium"
            >
              {equipementLabel(value)}
              <button
                type="button"
                onClick={() => removeCustom(value)}
                className="rounded-full p-0.5 text-muted-foreground hover:text-foreground"
                aria-label={`Retirer ${equipementLabel(value)}`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
