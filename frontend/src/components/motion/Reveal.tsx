import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type RevealFrom = "up" | "left" | "right" | "scale" | "blur";

/**
 * Révèle son contenu quand il entre dans le viewport (une seule fois).
 *
 * Sur la landing, les transitions restent actives même si
 * `prefers-reduced-motion` est activé (page marketing intentionnellement
 * dynamique). Ailleurs, le réglage système est respecté.
 */
export function Reveal({
  children,
  className,
  from = "up",
  delay = 0,
  as: Tag = "div",
  /** Fraction visible avant déclenchement (0–1). */
  threshold = 0.12,
  /**
   * Si true (défaut pour pages marketing), anime même sous
   * prefers-reduced-motion. Passez false pour respecter strictement le OS.
   */
  forceMotion = true,
}: {
  children: ReactNode;
  className?: string;
  from?: RevealFrom;
  delay?: number;
  as?: ElementType;
  threshold?: number;
  forceMotion?: boolean;
}) {
  const ref = useRef<HTMLElement>(null);
  // "idle" = pas encore pris en charge par le client → aucun style masquant.
  const [state, setState] = useState<"idle" | "hidden" | "shown">("idle");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (typeof window === "undefined" || typeof IntersectionObserver === "undefined") {
      setState("shown");
      return;
    }

    const reduced =
      !forceMotion && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setState("shown");
      return;
    }

    setState("hidden");

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setState("shown");
            observer.disconnect();
          }
        }
      },
      { threshold, rootMargin: "0px 0px -10% 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold, forceMotion]);

  return (
    <Tag
      ref={ref}
      className={cn(className)}
      data-reveal={state === "idle" ? undefined : state}
      data-reveal-from={from}
      style={delay ? ({ "--reveal-delay": `${delay}ms` } as React.CSSProperties) : undefined}
    >
      {children}
    </Tag>
  );
}
