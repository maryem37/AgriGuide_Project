import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/motion/Reveal";

/**
 * En-tête de page de l'app authentifiée : signal + titre + sous-titre,
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
    primary: "bg-primary text-signal",
    sky: "bg-sky/25 text-sky-foreground",
    earth: "bg-earth/15 text-earth",
    harvest: "bg-harvest/20 text-harvest-foreground",
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
      <div className="flex items-start gap-3.5">
        <div
          className={cn(
            "mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-transform duration-500 hover:scale-105",
            tones[tone],
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="h-1 w-8 rounded-full bg-signal mb-2.5" aria-hidden />
          <h1 className="font-display text-3xl md:text-[2.35rem] font-bold leading-[1.05] tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-muted-foreground mt-1.5 max-w-xl text-[0.95rem] leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </Reveal>
  );
}
