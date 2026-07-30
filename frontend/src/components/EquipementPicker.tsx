import { cn } from "@/lib/utils";
import { EQUIPEMENT_OPTIONS } from "@/lib/equipements";
import type { EquipementType } from "@/lib/authApi";

/** Sélecteur de matériel agricole détenu — cases à cocher visuelles (icône + nom). */
export function EquipementPicker({
  selected,
  onChange,
}: {
  selected: EquipementType[];
  onChange: (value: EquipementType[]) => void;
}) {
  function toggle(value: EquipementType) {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  }

  return (
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
    </div>
  );
}
