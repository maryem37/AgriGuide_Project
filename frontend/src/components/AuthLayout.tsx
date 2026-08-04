import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { AgriLogo } from "@/components/AgriLogo";
import { HeroMedia } from "@/components/motion/HeroMedia";

/** Arguments affichés sur le panneau visuel (desktop uniquement). */
const HIGHLIGHTS = [
  "Analyse de parcelle : sol, climat, auxiliaires",
  "Trois scénarios budgétaires chiffrés",
  "Aides et réglementation expliquées",
] as const;

/**
 * Écran d'authentification en deux volets : formulaire à gauche, panneau
 * photo animé à droite (masqué sous `lg` pour laisser la place au clavier
 * sur mobile).
 */
export function AuthLayout({
  children,
  title,
  subtitle,
  maxWidth = "max-w-lg",
}: {
  children: ReactNode;
  title: string;
  subtitle?: string;
  maxWidth?: string;
}) {
  return (
    <div className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,42rem)]">
      {/* Volet formulaire */}
      <div className="flex flex-col px-4 py-8 md:py-12">
        <div className={`mx-auto flex w-full flex-1 flex-col ${maxWidth}`}>
          <div className="landing-rise flex items-center justify-between gap-4">
            <Link to="/" className="press inline-flex">
              <AgriLogo withWordmark size={44} />
            </Link>
            <Link
              to="/"
              className="nudge-x inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="nudge-target h-4 w-4" />
              Accueil
            </Link>
          </div>

          <div className="mt-10">
            <h1 className="landing-rise landing-rise-delay-1 font-display text-3xl md:text-4xl font-semibold">
              {title}
            </h1>
            {subtitle && (
              <p className="landing-rise landing-rise-delay-2 mt-2 text-muted-foreground">
                {subtitle}
              </p>
            )}
          </div>

          <div className="landing-rise landing-rise-delay-3 mt-8">{children}</div>
        </div>
      </div>

      {/* Volet visuel */}
      <div className="relative hidden overflow-hidden lg:block">
        <HeroMedia poster="/img/journey/agriculture.jpg" alt="" objectPosition="center 45%" />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(200deg, rgba(28,43,28,0.15) 0%, rgba(28,43,28,0.55) 55%, rgba(28,43,28,0.88) 100%)",
          }}
          aria-hidden
        />
        <div className="relative flex h-full flex-col justify-end p-10 xl:p-14">
          <p className="landing-rise font-display text-3xl font-semibold leading-tight text-white xl:text-4xl">
            Le conseil de terrain,
            <br />
            au même endroit.
          </p>
          <ul className="mt-8 space-y-3">
            {HIGHLIGHTS.map((item, i) => (
              <li
                key={item}
                className="landing-rise flex items-center gap-3 text-white/85"
                style={{ animationDelay: `${0.15 + i * 0.12}s` }}
              >
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-white/70" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
