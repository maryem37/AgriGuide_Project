import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Fond plein écran : photo (Ken Burns optionnel) et/ou vidéo.
 * Avec `videoSrc`, la photo n’est pas affichée — seule la vidéo compte.
 */
export function HeroMedia({
  poster,
  videoSrc,
  alt,
  className,
  objectPosition = "center center",
  kenBurns = true,
  /** Flou + éclaircissement de la vidéo (landing). */
  soften = false,
}: {
  poster?: string;
  videoSrc?: string;
  alt: string;
  className?: string;
  objectPosition?: string;
  kenBurns?: boolean;
  soften?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [allowKenBurns, setAllowKenBurns] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setAllowKenBurns(kenBurns && !reduced && !videoSrc);
  }, [kenBurns, videoSrc]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoSrc) return;

    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");

    const tryPlay = () => {
      void video.play().catch(() => {});
    };

    tryPlay();
    video.addEventListener("loadeddata", tryPlay);
    video.addEventListener("canplay", tryPlay);

    return () => {
      video.removeEventListener("loadeddata", tryPlay);
      video.removeEventListener("canplay", tryPlay);
    };
  }, [videoSrc]);

  const showPoster = Boolean(poster) && !videoSrc;

  return (
    <div
      className={cn("pointer-events-none absolute inset-0 z-0 overflow-hidden", className)}
      aria-hidden={!alt}
    >
      {showPoster && (
        <img
          src={poster}
          alt={alt}
          className={cn(
            "absolute inset-0 z-0 h-full w-full object-cover",
            allowKenBurns && "ken-burns",
          )}
          style={{ objectPosition }}
          fetchPriority="high"
        />
      )}

      {videoSrc && (
        <video
          ref={videoRef}
          className={cn(
            "absolute inset-0 z-[1] h-full w-full scale-105 object-cover",
            soften && "brightness-110 contrast-95 saturate-90",
          )}
          style={{ objectPosition }}
          src={videoSrc}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          tabIndex={-1}
        />
      )}
    </div>
  );
}
