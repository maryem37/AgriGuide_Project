import { useEffect, useRef, useState } from "react";
import { MarkdownLite } from "@/lib/markdownLite";

/**
 * Affiche la réponse en streaming mot à mot (effet chatbot),
 * puis laisse le markdown final s'afficher.
 */
export function TypewriterMarkdown({
  text,
  wordsPerTick = 1,
  tickMs = 45,
  onProgress,
  onDone,
}: {
  text: string;
  wordsPerTick?: number;
  tickMs?: number;
  onProgress?: () => void;
  onDone?: () => void;
}) {
  // Tokens = mots + espaces capturés, pour conserver la mise en page.
  const tokens = useRef<string[]>([]);
  tokens.current = text.length ? text.split(/(\s+)/).filter((t) => t.length > 0) : [];

  const [visibleCount, setVisibleCount] = useState(0);
  const doneFired = useRef(false);
  const onDoneRef = useRef(onDone);
  const onProgressRef = useRef(onProgress);
  onDoneRef.current = onDone;
  onProgressRef.current = onProgress;

  const total = tokens.current.length;
  const done = total > 0 && visibleCount >= total;
  const visible = tokens.current.slice(0, visibleCount).join("");

  // Reset quand le texte change.
  useEffect(() => {
    doneFired.current = false;
    setVisibleCount(0);
  }, [text]);

  // Boucle de frappe — indépendante de `done` dans les deps pour éviter
  // de redémarrer / couper l'intervalle à chaque tick.
  useEffect(() => {
    if (!text.trim()) {
      if (!doneFired.current) {
        doneFired.current = true;
        onDoneRef.current?.();
      }
      return;
    }

    let cancelled = false;
    const step = Math.max(1, wordsPerTick);
    const id = window.setInterval(() => {
      if (cancelled) return;
      setVisibleCount((current) => {
        const max = tokens.current.length;
        if (current >= max) return current;
        const next = Math.min(current + step, max);
        onProgressRef.current?.();
        return next;
      });
    }, Math.max(16, tickMs));

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [text, wordsPerTick, tickMs]);

  useEffect(() => {
    if (!done || doneFired.current) return;
    doneFired.current = true;
    onDoneRef.current?.();
  }, [done]);

  return (
    <div className="relative text-sm leading-relaxed">
      <MarkdownLite text={visible.length > 0 ? visible : "\u00A0"} />
      {!done && (
        <span
          className="chat-caret ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-primary align-middle"
          aria-hidden
        />
      )}
    </div>
  );
}
