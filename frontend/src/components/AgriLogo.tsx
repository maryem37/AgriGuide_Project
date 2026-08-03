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
 * Marque AgriMent : feuille nette + coccinelle rouge classique (auxiliaire).
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
        aria-hidden
      >
        <svg
          viewBox="0 0 64 64"
          width={size * 0.88}
          height={size * 0.88}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="agrilogo-mark"
        >
          {/* Leaf — full, readable silhouette */}
          <path
            d="M18 46c0-14 8-26 20-34 2 10 4 20 2 32-8 4-16 5-22 2z"
            fill="#3D8B40"
          />
          <path
            d="M20 44c6-2 12-2 18 0"
            stroke="#2E6B32"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.55"
          />
          {/* Midrib */}
          <path
            d="M36 14c-1 10-2 20-1 30"
            stroke="#1E4D22"
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Side veins */}
          <path
            d="M34 22c-5 2-9 5-11 8M35 30c-5 2-9 4-12 6M35 38c-4 1-8 2-11 3"
            stroke="#1E4D22"
            strokeWidth="1.4"
            strokeLinecap="round"
            opacity="0.7"
          />

          {/* Ladybug — larger, classic red, clear spots */}
          <g className="agrilogo-bug">
            {/* Soft contact shadow on leaf */}
            <ellipse cx="42" cy="44" rx="14" ry="4" fill="#1A2E14" opacity="0.12" />
            {/* Body */}
            <ellipse cx="42" cy="38" rx="13" ry="11.5" fill="#E53935" />
            {/* Wing divide */}
            <path
              d="M42 27.5v21"
              stroke="#1A1A1A"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
            {/* Spots */}
            <circle cx="36.5" cy="34" r="2.6" fill="#1A1A1A" />
            <circle cx="47.5" cy="33.5" r="2.4" fill="#1A1A1A" />
            <circle cx="37.5" cy="42" r="2.2" fill="#1A1A1A" />
            <circle cx="47" cy="41.5" r="2.3" fill="#1A1A1A" />
            {/* Head */}
            <circle cx="54.5" cy="37.5" r="5.2" fill="#1A1A1A" />
            {/* Eye glint */}
            <circle cx="56.2" cy="36.2" r="1.2" fill="#F5F5F5" opacity="0.85" />
            {/* Antennae */}
            <path
              d="M56.5 33.2c1.8-3.5 4.5-5.2 7-5.5M57.2 35c2.4-2.2 5.2-2.6 7.2-1.4"
              stroke="#1A1A1A"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </g>
        </svg>
      </span>
      {withWordmark && (
        <span className="leading-none">
          <span
            className={cn(
              "font-display text-xl font-semibold tracking-tight",
              onDark ? "text-white" : "text-foreground",
            )}
          >
            AgriMent
          </span>
          {tagline && (
            <span
              className={cn(
                "mt-1 block text-[11px] font-medium tracking-wide",
                onDark ? "text-white/70" : "text-muted-foreground",
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
