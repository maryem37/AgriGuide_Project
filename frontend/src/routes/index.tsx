import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgriLogo } from "@/components/AgriLogo";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AgriMent — Bienvenue" },
      {
        name: "description",
        content:
          "AgriMent accompagne les agriculteurs : parcelle, insectes auxiliaires, budget et aides — avec Mistral.",
      },
      { property: "og:title", content: "AgriMent — Bienvenue" },
      {
        property: "og:description",
        content:
          "Du sol aux insectes du champ, un conseil agricole clair. En partenariat avec Mistral.",
      },
    ],
  }),
  component: Welcome,
});

function Welcome() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#E7F0E8] text-[#1C2B1C] flex flex-col">
      {/* Hero — one composition: brand, line, sentence, CTAs, full-bleed field */}
      <section className="relative min-h-[100svh] flex flex-col">
        <img
          src="/img/landing-hero-field.jpg?v=2"
          alt="Coccinelle sur une feuille au bord d’un champ"
          className="absolute inset-0 h-full w-full object-cover object-[center_40%]"
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(231,240,232,0.55) 0%, rgba(231,240,232,0.15) 28%, rgba(28,43,28,0.15) 55%, rgba(28,43,28,0.72) 100%)",
          }}
          aria-hidden
        />

        <header className="relative z-10 flex items-center justify-between gap-4 px-5 pt-7 md:px-10 md:pt-9">
          <AgriLogo size={42} withWordmark tagline={null} className="landing-rise [&_span]:!text-[#1C2B1C]" />
          <Link
            to="/connexion"
            className="landing-rise landing-rise-delay-1 text-sm font-semibold text-[#1C2B1C]/80 underline-offset-4 hover:underline"
          >
            Connexion
          </Link>
        </header>

        <div className="relative z-10 mt-auto px-5 pb-14 pt-24 md:px-10 md:pb-20">
          <div className="max-w-3xl">
            <p className="landing-rise font-display text-[clamp(3.5rem,11vw,7rem)] font-semibold leading-[0.9] tracking-tight text-white drop-shadow-sm">
              AgriMent
            </p>
            <h1 className="landing-rise landing-rise-delay-1 mt-5 max-w-lg font-display text-xl md:text-2xl font-medium leading-snug text-white/95">
              Cultiver avec le vivant — y compris les insectes du champ.
            </h1>
            <p className="landing-rise landing-rise-delay-2 mt-3 max-w-md text-base text-white/80 leading-relaxed">
              Un conseiller de terrain pour vos cultures, votre budget et vos aides. Construit avec
              Mistral.
            </p>
            <div className="landing-rise landing-rise-delay-3 mt-8 flex flex-col sm:flex-row gap-3">
              <Button
                asChild
                size="lg"
                className="h-14 px-7 text-base rounded-xl bg-white text-[#1C2B1C] hover:bg-white/90 font-semibold"
              >
                <Link to="/inscription">
                  Créer un compte <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-14 px-7 text-base rounded-xl border-white/50 bg-transparent text-white hover:bg-white/10 hover:text-white"
              >
                <Link to="/connexion">Se connecter</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Single purpose: what you get — open layout, no card grid */}
      <section className="px-5 py-16 md:px-10 md:py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight max-w-xl">
            Trois regards sur votre exploitation
          </h2>
          <p className="mt-3 max-w-lg text-[#1C2B1C]/65">
            Agriculture, business et réglementation — reliés, sans vous noyer sous les tableaux.
          </p>

          <div className="mt-14 space-y-0 divide-y divide-[#1C2B1C]/12">
            {[
              {
                title: "Le champ & ses insectes",
                body: "Analysez votre parcelle, le sol, le climat — et les signaux du vivant. Les auxiliaires comptent autant que le rendement.",
              },
              {
                title: "Le budget qui tient",
                body: "Saisissez votre enveloppe, générez l’étude financière et comparez des scénarios de cultures réalistes.",
              },
              {
                title: "Les règles, dites simplement",
                body: "Aides, cadre PAC et obligations expliqués comme à un voisin — pas comme un formulaire.",
              },
            ].map((row, i) => (
              <div
                key={row.title}
                className="grid gap-3 py-8 md:grid-cols-[8rem_1fr] md:gap-10 md:py-10"
              >
                <span className="font-display text-4xl font-semibold text-[#5A8F4A]/45 tabular-nums">
                  0{i + 1}
                </span>
                <div>
                  <h3 className="font-display text-2xl font-semibold">{row.title}</h3>
                  <p className="mt-2 max-w-xl text-[#1C2B1C]/65 leading-relaxed">{row.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Insect motif band */}
      <section className="relative overflow-hidden bg-[#2F5230] text-[#E7F0E8] px-5 py-16 md:px-10 md:py-20">
        <LadybugTrail className="pointer-events-none absolute -right-6 top-8 h-40 w-40 opacity-20 md:right-16 md:top-12 md:h-56 md:w-56 landing-float" />
        <div className="relative mx-auto max-w-5xl md:pr-48">
          <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight">
            Pourquoi une coccinelle sur le logo&nbsp;?
          </h2>
          <p className="mt-4 max-w-xl text-[#E7F0E8]/75 leading-relaxed">
            Parce que l’agriculture durable s’écrit aussi avec ses alliés. AgriMent place les
            insectes auxiliaires au centre du récit produit — visibles pour vous, et pour nos
            partenaires.
          </p>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="px-5 py-16 md:px-10 md:py-20">
        <div className="mx-auto max-w-5xl flex flex-col md:flex-row md:items-end md:justify-between gap-8">
          <div>
            <h2 className="font-display text-3xl font-semibold tracking-tight">
              Prêt à regarder votre parcelle autrement&nbsp;?
            </h2>
            <p className="mt-3 max-w-sm text-[#1C2B1C]/65">
              Créez votre compte et lancez votre première analyse de terrain.
            </p>
          </div>
          <Button
            asChild
            size="lg"
            className="h-14 px-8 rounded-xl bg-[#2F5230] text-[#E7F0E8] hover:bg-[#264226] font-semibold"
          >
            <Link to="/inscription">
              Rejoindre AgriMent <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-[#1C2B1C]/12 bg-[#1C2B1C] text-[#E7F0E8]">
        <div className="mx-auto max-w-5xl px-5 py-12 md:px-10">
          <div className="flex flex-col gap-10 md:flex-row md:justify-between">
            <div>
              <AgriLogo size={44} withWordmark tagline="Conseil de terrain" variant="onDark" />
              <p className="mt-4 max-w-xs text-sm text-[#E7F0E8]/55 leading-relaxed">
                Assistant agricole pour cultiver, gérer et décider — du sol aux insectes du champ.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-10 sm:gap-16">
              <div>
                <div className="text-xs font-semibold tracking-[0.18em] uppercase text-[#E7F0E8]/40">
                  Compte
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  <li>
                    <Link to="/inscription" className="text-[#E7F0E8]/80 hover:text-white">
                      Créer un compte
                    </Link>
                  </li>
                  <li>
                    <Link to="/connexion" className="text-[#E7F0E8]/80 hover:text-white">
                      Se connecter
                    </Link>
                  </li>
                </ul>
              </div>
              <div>
                <div className="text-xs font-semibold tracking-[0.18em] uppercase text-[#E7F0E8]/40">
                  Produit
                </div>
                <ul className="mt-3 space-y-2 text-sm text-[#E7F0E8]/80">
                  <li>Cultures & insectes</li>
                  <li>Budget & scénarios</li>
                  <li>Réglementation</li>
                </ul>
              </div>
            </div>
          </div>
          <div className="mt-10 flex flex-col gap-2 border-t border-white/10 pt-6 text-xs text-[#E7F0E8]/40 sm:flex-row sm:items-center sm:justify-between">
            <span>© {new Date().getFullYear()} AgriMent. Tous droits réservés.</span>
            <span>Construit avec Mistral</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

/** Decorative ladybug silhouette for the insect band. */
function LadybugTrail({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" className={className} fill="none" aria-hidden>
      <ellipse cx="58" cy="68" rx="34" ry="30" fill="currentColor" />
      <path d="M24 68h68" stroke="#2F5230" strokeWidth="3" strokeLinecap="round" opacity="0.35" />
      <circle cx="42" cy="58" r="5" fill="#2F5230" opacity="0.4" />
      <circle cx="68" cy="56" r="4.5" fill="#2F5230" opacity="0.4" />
      <circle cx="55" cy="78" r="4" fill="#2F5230" opacity="0.4" />
      <circle cx="88" cy="66" r="12" fill="currentColor" />
      <path
        d="M94 56c4-8 10-12 16-13M96 62c6-5 12-6 18-3"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
