import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Check, LineChart, ScrollText, Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgriLogo } from "@/components/AgriLogo";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AgriMent — Bienvenue" },
      {
        name: "description",
        content:
          "AgriMent est la plateforme qui relie conseil agronomique, scénarios financiers et réglementation pour les exploitations agricoles.",
      },
      { property: "og:title", content: "AgriMent — Bienvenue" },
      {
        property: "og:description",
        content:
          "Analysez votre parcelle, simulez votre budget et comprenez vos aides — une seule plateforme, propulsée par Mistral.",
      },
    ],
  }),
  component: Welcome,
});

/** Parcours conseil — 3 étapes séquentielles (comme la référence visuelle). */
const JOURNEY = [
  {
    to: "/regulation" as const,
    step: 1,
    title: "Conseiller réglementaire",
    body: "Indiquez votre situation. Obtenez les règles applicables, les certifications, les aides et le cadre à respecter — sans jargon.",
    image: "/img/journey/regulation.jpg",
    icon: ScrollText,
    accent: "#2F5230",
    accentSoft: "rgba(47, 82, 48, 0.12)",
    points: [
      "Cadre légal par région",
      "Certifications qualité",
      "Aides & subventions",
      "Obligations expliquées clairement",
    ],
  },
  {
    to: "/agriculture" as const,
    step: 2,
    title: "Conseiller agricole",
    body: "Nous analysons votre parcelle, le sol, le climat et les signaux du vivant — dont les insectes auxiliaires — pour recommander les meilleures cultures.",
    image: "/img/journey/agriculture.jpg",
    icon: Sprout,
    accent: "#C46A2B",
    accentSoft: "rgba(196, 106, 43, 0.14)",
    points: [
      "Analyse du sol",
      "Lecture parcelle & climat",
      "Insectes auxiliaires",
      "Top cultures recommandées",
    ],
  },
  {
    to: "/business" as const,
    step: 3,
    title: "Conseiller business",
    body: "Équilibrez budget, étude de marché et risque pour obtenir des scénarios rentables et une vision claire de vos hectares.",
    image: "/img/journey/business.jpg",
    icon: LineChart,
    accent: "#2B6CB0",
    accentSoft: "rgba(43, 108, 176, 0.14)",
    points: [
      "3 scénarios optimisés",
      "Score de matching",
      "Allocation des hectares",
      "Profit & risque estimés",
    ],
  },
] as const;

const REFERENCES = [
  {
    name: "FAOSTAT",
    href: "https://www.fao.org/faostat/",
    src: "/img/references/faostat.gif",
  },
  {
    name: "FranceAgriMer",
    href: "https://www.franceagrimer.fr/",
    src: "/img/references/franceagrimer.jpg",
  },
  {
    name: "Légifrance",
    href: "https://www.legifrance.gouv.fr/",
    src: "/img/references/legifrance.jpg",
  },
  {
    name: "agriculture.gouv.fr",
    href: "https://agriculture.gouv.fr/",
    src: "/img/references/republique_france.png",
  },
] as const;

function Welcome() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#E7F0E8] text-[#1C2B1C] flex flex-col">
      {/* Hero */}
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
          <AgriLogo
            size={42}
            withWordmark
            tagline={null}
            className="landing-rise [&_span]:!text-[#1C2B1C]"
          />
          <Link
            to="/connexion"
            className="landing-rise landing-rise-delay-1 text-sm font-semibold text-[#1C2B1C]/80 underline-offset-4 hover:underline"
          >
            Connexion
          </Link>
        </header>

        <div className="relative z-10 mt-auto px-5 pb-14 pt-24 md:px-10 md:pb-20">
          <div className="max-w-2xl">
            <p className="landing-rise font-display text-[clamp(3.5rem,11vw,7rem)] font-semibold leading-[0.9] tracking-tight text-white drop-shadow-sm">
              AgriMent
            </p>
            <h1 className="landing-rise landing-rise-delay-1 mt-5 font-display text-xl md:text-2xl font-medium leading-snug text-white/95">
              La plateforme qui relie votre parcelle, votre budget et vos aides.
            </h1>
            <p className="landing-rise landing-rise-delay-2 mt-4 max-w-xl text-base md:text-[1.05rem] text-white/80 leading-relaxed">
              AgriMent aide les agriculteurs à décider sur le terrain : analyser une
              parcelle (sol, climat, insectes auxiliaires), simuler des scénarios
              financiers réalistes, et comprendre la réglementation et les aides —
              trois conseillers IA, une seule plateforme, propulsée avec Mistral.
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

      {/* Advisory journey — 3 sequential steps */}
      <section className="px-5 py-16 md:px-10 md:py-24 bg-[#F3F6F2]">
        <div className="mx-auto max-w-6xl">
          <div className="text-center max-w-2xl mx-auto">
            <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-[#2F5230]">
              Votre parcours conseil
            </h2>
            <p className="mt-3 text-[#1C2B1C]/65">
              Trois modules qui s’enchaînent — chacun s’appuie sur le précédent.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {JOURNEY.map((step) => {
              const Icon = step.icon;
              return (
                <Link
                  key={step.to}
                  to={step.to}
                  className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-[0_8px_30px_-18px_rgba(28,43,28,0.35)] ring-1 ring-[#1C2B1C]/08 transition hover:-translate-y-1 hover:shadow-[0_18px_40px_-20px_rgba(28,43,28,0.4)]"
                >
                  <div className="relative aspect-[16/10] overflow-hidden">
                    <img
                      src={step.image}
                      alt=""
                      className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
                      loading="lazy"
                    />
                    <div className="absolute left-3 top-3 flex items-center gap-2">
                      <span
                        className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white shadow-sm"
                        style={{ backgroundColor: step.accent }}
                      >
                        {step.step}
                      </span>
                      <span className="rounded-full bg-white/95 px-3 py-1 text-xs font-semibold text-[#1C2B1C] shadow-sm">
                        Étape {step.step} sur 3
                      </span>
                    </div>
                    <span className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm">
                      <Icon className="h-5 w-5" style={{ color: step.accent }} />
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col p-5 md:p-6">
                    <h3 className="font-display text-xl font-semibold tracking-tight text-[#1C2B1C]">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#1C2B1C]/65">{step.body}</p>
                    <ul className="mt-5 space-y-2.5">
                      {step.points.map((point) => (
                        <li key={point} className="flex items-start gap-2.5 text-sm text-[#1C2B1C]/80">
                          <span
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
                            style={{ backgroundColor: step.accentSoft, color: step.accent }}
                          >
                            <Check className="h-3 w-3" strokeWidth={3} />
                          </span>
                          {point}
                        </li>
                      ))}
                    </ul>
                    <span
                      className={cn(
                        "mt-6 inline-flex items-center gap-1.5 text-sm font-semibold",
                        "opacity-80 transition group-hover:opacity-100 group-hover:gap-2.5",
                      )}
                      style={{ color: step.accent }}
                    >
                      Ouvrir <ArrowRight className="h-4 w-4" />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="mt-10 flex justify-center">
            <Button
              asChild
              size="lg"
              className="h-14 px-7 rounded-xl bg-[#2F5230] text-[#E7F0E8] hover:bg-[#264226] font-semibold"
            >
              <Link to="/regulation">
                Commencer par l’étape 1 — Réglementation
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
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
                Plateforme de conseil agricole : cultures, budget et réglementation — du sol aux
                insectes du champ.
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
                  Conseillers
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  {JOURNEY.map((f) => (
                    <li key={f.to}>
                      <Link to={f.to} className="text-[#E7F0E8]/80 hover:text-white">
                        {f.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Data / legal references */}
          <div className="mt-12 border-t border-white/10 pt-8">
            <div className="text-xs font-semibold tracking-[0.18em] uppercase text-[#E7F0E8]/40">
              Sources & références
            </div>
            <p className="mt-2 max-w-2xl text-sm text-[#E7F0E8]/50">
              AgriMent s’appuie sur des données et référentiels publics pour ses analyses de marché
              et son conseil réglementaire.
            </p>
            <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {REFERENCES.map((ref) => (
                <li key={ref.name}>
                  <a
                    href={ref.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex h-24 flex-col items-center justify-center gap-1.5 rounded-xl bg-white px-3 py-3 transition hover:ring-2 hover:ring-[#D4F07A]/60"
                    title={`Ouvrir ${ref.name}`}
                  >
                    <img
                      src={ref.src}
                      alt={ref.name}
                      className="max-h-14 w-auto max-w-full object-contain"
                      loading="lazy"
                    />
                    <span className="text-[11px] font-medium text-[#1C2B1C]/65">{ref.name}</span>
                  </a>
                </li>
              ))}
            </ul>
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
