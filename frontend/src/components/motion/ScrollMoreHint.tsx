import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Flèche flottante en bas du viewport.
 * Portail sur `document.body` : évite le piège du `transform` sur `<main class="page-enter">`
 * qui casse `position: fixed`.
 */
function isModalOpen() {
  return Boolean(
    document.querySelector('[role="dialog"][data-state="open"], [data-radix-dialog-overlay][data-state="open"]'),
  );
}

export function ScrollMoreHint({ className }: { className?: string }) {
  const endRef = useRef<HTMLDivElement>(null);
  const [canScrollMore, setCanScrollMore] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const end = endRef.current;
    if (!end || typeof IntersectionObserver === "undefined") {
      setCanScrollMore(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Flèche visible tant que le bas de page n’est pas encore à l’écran.
        setCanScrollMore(!entry.isIntersecting);
      },
      { root: null, threshold: 0, rootMargin: "0px 0px -40px 0px" },
    );
    observer.observe(end);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setModalOpen(isModalOpen());
    const observer = new MutationObserver(() => setModalOpen(isModalOpen()));
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["data-state"],
    });
    return () => observer.disconnect();
  }, []);

  const visible = canScrollMore && !modalOpen;

  const scrollAhead = () => {
    window.scrollBy({ top: Math.round(window.innerHeight * 0.6), behavior: "smooth" });
  };

  const arrow =
    mounted &&
    createPortal(
      <button
        type="button"
        aria-label="Faire défiler vers le bas"
        tabIndex={visible ? 0 : -1}
        onClick={scrollAhead}
        className={cn(
          "scroll-hint-float fixed left-1/2 z-[100] -translate-x-1/2",
          "bottom-24 md:bottom-10",
          "flex h-8 w-8 items-center justify-center rounded-full",
          "border border-primary/25 bg-primary/35 text-primary-foreground/95",
          "shadow-[0_6px_18px_-8px_rgba(47,82,48,0.4)] backdrop-blur-[2px]",
          "transition-[opacity,transform] duration-300 ease-out",
          "hover:bg-primary/55 hover:border-primary/40",
          "active:scale-95",
          visible
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
          className,
        )}
      >
        <ChevronDown className="scroll-hint-arrow h-4 w-4" strokeWidth={2.25} />
      </button>,
      document.body,
    );

  return (
    <>
      {/* Sentinelle en fin de page : quand elle entre dans le viewport, on cache la flèche */}
      <div ref={endRef} className="h-px w-full" aria-hidden />
      {arrow}
    </>
  );
}
