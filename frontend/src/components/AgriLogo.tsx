import { cn } from "@/lib/utils";

type AgriLogoProps = {
  className?: string;
  /** Mark size in px (square). */
  size?: number;
  /** Show wordmark next to the mark. */
  withWordmark?: boolean;
  /** Line under the name; pass `null` to hide. */
  tagline?: string | null;
  /** Invert colors for dark / photo backgrounds. */
  variant?: "default" | "onDark";
};

/**
 * Marque AgriMent — fichier `public/Logo.png`.
 */
export function AgriLogo({
  className,
  size = 44,
  withWordmark = false,
  tagline = "Auxiliaires & cultures",
  variant = "default",
}: AgriLogoProps) {
  const onDark = variant === "onDark";

  return (
    <span className={cn("inline-flex items-center gap-3", className)}>
      <span
        className={cn(
          "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-2xl",
          onDark ? "bg-white/95" : "bg-white",
          "ring-1 ring-black/8",
        )}
        style={{ width: size, height: size }}
      >
        <img
          src="/Logo.png"
          alt="AgriMent"
          width={size}
          height={size}
          className="h-full w-full object-contain"
          decoding="async"
        />
      </span>
      {withWordmark && (
        <span className="leading-none">
          <span
            className={cn(
              "font-display text-xl font-bold tracking-tight",
              onDark ? "text-white" : "text-foreground",
            )}
          >
            Agri<span className={onDark ? "text-signal" : "text-primary"}>Ment</span>
          </span>
          {tagline && (
            <span
              className={cn(
                "mt-1 block font-mono text-[10px] font-medium uppercase tracking-[0.16em]",
                onDark ? "text-white/55" : "text-muted-foreground",
              )}
            >
              {tagline}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
