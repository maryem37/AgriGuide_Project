import { useEffect, useRef, useState } from "react";

/**
 * Compte de 0 → `value` dès que l'élément retourné entre dans le viewport.
 *
 * Retourne `[ref, displayed]` : branchez `ref` sur le nœud à observer et
 * affichez `displayed`. Respecte `prefers-reduced-motion` (valeur finale
 * affichée immédiatement).
 */
export function useCountUp<T extends HTMLElement = HTMLSpanElement>(
  value: number,
  { duration = 1200, decimals = 0 }: { duration?: number; decimals?: number } = {},
) {
  const ref = useRef<T>(null);
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (
      typeof window === "undefined" ||
      typeof IntersectionObserver === "undefined" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setDisplayed(value);
      return;
    }

    let frame = 0;
    let start: number | null = null;

    const run = (now: number) => {
      if (start === null) start = now;
      const progress = Math.min((now - start) / duration, 1);
      // easeOutCubic - décélération naturelle en fin de course.
      const eased = 1 - Math.pow(1 - progress, 3);
      const factor = 10 ** decimals;
      setDisplayed(Math.round(value * eased * factor) / factor);
      if (progress < 1) frame = requestAnimationFrame(run);
    };

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            frame = requestAnimationFrame(run);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(el);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [value, duration, decimals]);

  return [ref, displayed] as const;
}
