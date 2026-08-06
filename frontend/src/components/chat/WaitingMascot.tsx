/**
 * Indicateur d'attente style chatbot — pastille orange type Mistral + points.
 */
export function WaitingMascot({ label = "Réflexion en cours…" }: { label?: string }) {
  return (
    <div
      className="flex items-center gap-3 rounded-2xl rounded-tl-md border border-border/50 bg-background/95 px-3.5 py-2.5 shadow-sm"
      role="status"
      aria-live="polite"
    >
      <div
        className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#FF7000] text-white shadow-[0_0_0_3px_rgba(255,112,0,0.18)]"
        aria-hidden
      >
        {/* Marque simplifiée inspirée du logo Mistral (étoile / scintillement) */}
        <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] chat-mascot-soft" fill="currentColor">
          <path d="M12 2.5 13.4 9.2 19.5 8l-4.6 4.2 3.2 5.8L12 14.8 5.9 18l3.2-5.8L4.5 8l6.1 1.2L12 2.5Z" />
        </svg>
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="font-medium text-[#FF7000]/90">Mistral</span>
          <span aria-hidden>·</span>
          génération
          <span className="ml-0.5 flex gap-1" aria-hidden>
            {[0, 1, 2].map((d) => (
              <span
                key={d}
                className="mt-1.5 h-1 w-1 rounded-full bg-[#FF7000]/80"
                style={{
                  animation: "chat-dot-bounce 1s ease-in-out infinite",
                  animationDelay: `${d * 0.14}s`,
                }}
              />
            ))}
          </span>
        </p>
      </div>
    </div>
  );
}
