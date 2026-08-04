import { useState } from "react";
import { Check, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { EQUIPEMENT_OPTIONS, equipementLabel, slugifyEquipement } from "@/lib/equipements";
import type { EquipementType } from "@/lib/authApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Sélecteur de matériel agricole détenu - vignettes photo cochables (photo + nom). */
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
        {EQUIPEMENT_OPTIONS.map(({ value, label, icon: Icon, image }, i) => {
          const active = selected.includes(value);
          return (
            <button
              key={value}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(value)}
              style={{ animationDelay: `${i * 45}ms` }}
              className={cn(
                "page-enter press group relative flex flex-col overflow-hidden rounded-2xl border text-center transition-all duration-300",
                active
                  ? "border-primary ring-2 ring-primary/25 shadow-soft"
                  : "border-border hover:border-primary/40 hover:-translate-y-0.5 hover:shadow-soft",
              )}
            >
              {/* Photo du matériel - repli sur l'icône si l'image manque. */}
              <span className="relative block aspect-[4/3] w-full overflow-hidden bg-secondary">
                <img
                  src={image}
                  alt=""
                  loading="lazy"
                  className={cn(
                    "h-full w-full object-cover transition-all duration-500 group-hover:scale-105",
                    active ? "saturate-110" : "saturate-75 group-hover:saturate-100",
                  )}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
                <span
                  className={cn(
                    "absolute inset-0 transition-opacity duration-300",
                    active ? "opacity-0" : "opacity-100 group-hover:opacity-40",
                  )}
                  style={{ background: "rgba(28,43,28,0.28)" }}
                  aria-hidden
                />
                {/* Pastille de sélection animée. */}
                <span
                  className={cn(
                    "absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm transition-all duration-300",
                    active ? "scale-100 opacity-100" : "scale-50 opacity-0",
                  )}
                  aria-hidden
                >
                  <Check className="h-3.5 w-3.5" strokeWidth={3} />
                </span>
              </span>

              <span
                className={cn(
                  "flex flex-1 items-center justify-center gap-1.5 px-2 py-2.5 text-xs font-medium leading-tight transition-colors",
                  active ? "bg-primary/8 text-primary" : "bg-card text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {label}
              </span>
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
            "press flex flex-col items-center justify-center gap-2 rounded-2xl border p-4 text-center transition-all duration-300",
            showOther
              ? "border-primary bg-primary/5 ring-2 ring-primary/20"
              : "border-dashed border-border bg-card hover:border-primary/40 hover:-translate-y-0.5",
          )}
        >
          <div
            className={cn(
              "h-12 w-12 rounded-xl flex items-center justify-center transition-all duration-300",
              showOther
                ? "bg-primary text-primary-foreground rotate-45"
                : "bg-secondary text-foreground",
            )}
          >
            <Plus className="h-6 w-6" />
          </div>
          <span className="text-xs font-medium leading-tight">Autres</span>
        </button>
      </div>

      {showOther && (
        <div className="page-enter flex flex-col sm:flex-row gap-2 sm:items-start rounded-2xl border border-border bg-muted/30 p-3">
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
          {customSelected.map((value, i) => (
            <li
              key={value}
              style={{ animationDelay: `${i * 50}ms` }}
              className="page-enter inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-medium transition-transform duration-300 hover:-translate-y-0.5"
            >
              {equipementLabel(value)}
              <button
                type="button"
                onClick={() => removeCustom(value)}
                className="rounded-full p-0.5 text-muted-foreground transition-all duration-200 hover:rotate-90 hover:text-destructive"
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
