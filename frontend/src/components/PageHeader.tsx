import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/motion/Reveal";

/**
 * En-tête de page de l'app authentifiée : pastille d'icône + titre + sous-titre,
 * avec une entrée animée au scroll / au montage.
 */
export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  action,
  /** Teinte de la pastille - par défaut la couleur primaire. */
  tone = "primary",
  className,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  tone?: "primary" | "sky" | "earth" | "harvest" | "waste";
  className?: string;
}) {
  const tones: Record<string, string> = {
    primary: "bg-primary/10 text-primary",
    sky: "bg-sky/25 text-sky-foreground",
    earth: "bg-earth/15 text-earth",
    harvest: "bg-harvest/15 text-harvest",
    waste: "bg-waste/20 text-waste-foreground",
  };

  return (
    <Reveal
      from="up"
      className={cn(
        "flex flex-col gap-4 md:flex-row md:items-end md:justify-between",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-transform duration-500 hover:scale-105 hover:rotate-3",
            tones[tone],
          )}
        >
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-1">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </Reveal>
  );
}
