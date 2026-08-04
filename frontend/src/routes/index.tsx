import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Check, ChevronDown, LineChart, ScrollText, Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgriLogo } from "@/components/AgriLogo";
import { Reveal } from "@/components/motion/Reveal";
import { HeroMedia } from "@/components/motion/HeroMedia";
import { useCountUp } from "@/components/motion/useCountUp";
import { EQUIPEMENT_OPTIONS } from "@/lib/equipements";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AgriMent - Bienvenue" },
      {
        name: "description",
        content:
          "AgriMent est la plateforme qui relie conseil agronomique, scénarios financiers et réglementation pour les exploitations agricoles.",
      },
      { property: "og:title", content: "AgriMent - Bienvenue" },
      {
        property: "og:description",
        content:
          "Analysez votre parcelle, simulez votre budget et comprenez vos aides - une seule plateforme, propulsée par Mistral.",
      },
    ],
  }),
  component: Welcome,
});

/** Parcours conseil - 3 étapes séquentielles (agriculture → business → réglementation). */
const JOURNEY = [
  {
    to: "/agriculture" as const,
    step: 1,
    title: "Conseiller agricole",
    body: "Nous analysons votre parcelle, le sol, le climat et les signaux du vivant - dont les insectes auxiliaires - pour recommander les meilleures cultures.",
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
    step: 2,
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
  {
    to: "/regulation" as const,
    step: 3,
    title: "Conseiller réglementaire",
    body: "Indiquez votre situation. Obtenez les règles applicables, les certifications, les aides et le cadre à respecter - sans jargon.",
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
] as const;

const HERO_IMAGE = "/img/landing-hero-field.jpg?v=2";
const HERO_VIDEO = "/video/LandingPage.mp4";

const STATS = [
  { value: 3, suffix: "", label: "conseillers IA", sub: "Agricole, business, réglementaire" },
  { value: 5, suffix: "", label: "cultures classées", sub: "Par parcelle analysée" },
  { value: 800, suffix: " m", label: "rayon de voisinage", sub: "Contexte cultural réel" },
  {
    value: 100,
    suffix: " %",
    label: "sources publiques",
    sub: "FAOSTAT, FranceAgriMer, Légifrance",
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
    <div className="landing-page min-h-screen w-full overflow-x-hidden bg-[#E7F0E8] text-[#1C2B1C] flex flex-col">
      {/* Hero - vidéo plein écran */}
      <section className="relative isolate h-[100svh] min-h-[560px] w-full overflow-hidden bg-[#1C2B1C]">
        <HeroMedia
          videoSrc={HERO_VIDEO}
          alt="Champ agricole en mouvement"
          objectPosition="center 40%"
          soften
        />
        <div
          className="pointer-events-none absolute inset-0 z-[2]"
          style={{
            background:
              "linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(28,43,28,0.12) 42%, rgba(28,43,28,0.48) 100%)",
          }}
          aria-hidden
        />

        <header className="relative z-10 flex items-center justify-between gap-4 px-5 pt-7 md:px-10 md:pt-9">
          <AgriLogo
            size={42}
            withWordmark
            tagline={null}
            className="landing-rise [&_span]:!text-white"
          />
          <Link
            to="/connexion"
            className="landing-rise landing-rise-delay-1 rounded-full bg-transparent px-5 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Connexion
          </Link>
        </header>

        <div className="relative z-10 flex min-h-[calc(100svh-5.5rem)] flex-col justify-end px-5 pb-14 pt-24 md:px-10 md:pb-20">
          <div className="max-w-2xl">
            <h1 className="landing-rise font-display text-[clamp(2.4rem,7vw,4.25rem)] font-semibold leading-[1.05] tracking-tight text-white drop-shadow-sm">
              Cultiver un monde{" "}
              <span className="text-[#E8C04A]">plus</span> prévisible,{" "}
              <span className="text-[#E8C04A]">plus</span> rentable.
            </h1>
            <p className="landing-rise landing-rise-delay-1 mt-5 max-w-xl text-base md:text-[1.05rem] text-white/85 leading-relaxed">
              AgriMent aide les agriculteurs à décider sur le terrain : analyser une parcelle (sol,
              climat, insectes auxiliaires), simuler des scénarios financiers réalistes, et
              comprendre la réglementation et les aides - trois conseillers IA, une seule
              plateforme, propulsée avec Mistral.
            </p>
            <div className="landing-rise landing-rise-delay-2 mt-8 flex flex-col sm:flex-row gap-3">
              <Button
                asChild
                size="lg"
                className="press h-14 px-8 text-base rounded-full bg-[#E8C04A] text-[#1C2B1C] hover:bg-[#d4ad3a] font-semibold shadow-lg shadow-black/15 transition-transform hover:-translate-y-0.5"
              >
                <Link to="/inscription" className="nudge-x">
                  Créer un compte <ArrowRight className="nudge-target ml-2 h-5 w-5" />
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

          <div className="mt-10 flex justify-center md:mt-14">
            <span className="float-soft flex flex-col items-center gap-1 text-white/70">
              <span className="text-[11px] font-medium tracking-[0.2em] uppercase">Découvrir</span>
              <ChevronDown className="h-5 w-5" />
            </span>
          </div>
        </div>
      </section>

      {/* Comment ça marche */}
      <section className="bg-white px-5 py-16 md:px-10 md:py-24">
        <div className="mx-auto grid max-w-6xl items-center gap-10 md:grid-cols-2 md:gap-14">
          <Reveal from="left">
            <div className="overflow-hidden rounded-3xl shadow-[0_18px_50px_-28px_rgba(28,43,28,0.45)] ring-1 ring-[#1C2B1C]/08">
              <img
                src={HERO_IMAGE}
                alt="Champ agricole avec une coccinelle sur une feuille"
                className="aspect-[4/3] h-full w-full object-cover"
                loading="lazy"
              />
            </div>
          </Reveal>
          <Reveal from="right" delay={120}>
            <p className="text-xs font-semibold tracking-[0.22em] uppercase text-[#1C2B1C]/45">
              Comment ça marche
            </p>
            <h2 className="mt-3 font-display text-3xl md:text-4xl font-semibold tracking-tight text-[#1C2B1C] leading-tight">
              Une seule plateforme, du sol à la décision
            </h2>
            <p className="mt-4 text-base leading-relaxed text-[#1C2B1C]/65">
              Renseignez votre parcelle une fois. AgriMent connecte automatiquement le conseil
              réglementaire, l’analyse agronomique et la simulation financière - vous gardez la
              main sur chaque décision, sans ressaisir vos données à chaque étape.
            </p>
            <Button
              asChild
              size="lg"
              className="press mt-8 h-12 rounded-full bg-[#2F5230] px-7 text-base font-semibold text-[#E7F0E8] hover:bg-[#264226] transition-transform hover:-translate-y-0.5"
            >
              <Link to="/inscription" className="nudge-x">
                Découvrir la démarche <ArrowRight className="nudge-target ml-2 h-5 w-5" />
              </Link>
            </Button>
          </Reveal>
        </div>
      </section>

      <div className="landing-section-divider" aria-hidden />

      {/* Parcours conseil - fond blanc */}
      <section className="px-5 py-16 md:px-10 md:py-24 bg-[#F3F6F2]">
        <div className="mx-auto max-w-6xl">
          <Reveal className="text-center max-w-2xl mx-auto" delay={0}>
            <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-[#2F5230]">
              Votre parcours conseil
            </h2>
            <p className="mt-3 text-[#1C2B1C]/65">
              Trois modules qui s’enchaînent - chacun s’appuie sur le précédent.
            </p>
          </Reveal>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {JOURNEY.map((step, i) => {
              const Icon = step.icon;
              return (
                <Reveal key={step.to} from="up" delay={180 + i * 180} className="flex">
                  <Link
                    to={step.to}
                    className="group zoom-media nudge-x flex flex-1 flex-col overflow-hidden rounded-2xl bg-[#F7FAF7] shadow-[0_8px_30px_-18px_rgba(28,43,28,0.35)] ring-1 ring-[#1C2B1C]/08 transition-all duration-400 hover:-translate-y-1.5 hover:shadow-[0_22px_48px_-20px_rgba(28,43,28,0.45)]"
                  >
                    <div className="relative aspect-[16/10] overflow-hidden">
                      <img
                        src={step.image}
                        alt=""
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                      <div
                        className="absolute inset-0 opacity-100 transition-opacity duration-500 group-hover:opacity-0"
                        style={{
                          background:
                            "linear-gradient(180deg, rgba(28,43,28,0) 45%, rgba(28,43,28,0.28) 100%)",
                        }}
                        aria-hidden
                      />
                      <div className="absolute left-3 top-3 flex items-center gap-2">
                        <span
                          className="relative flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white shadow-sm transition-transform duration-400 group-hover:scale-110"
                          style={{ backgroundColor: step.accent }}
                        >
                          {step.step}
                        </span>
                        <span className="rounded-full bg-white/95 px-3 py-1 text-xs font-semibold text-[#1C2B1C] shadow-sm backdrop-blur-sm">
                          Étape {step.step} sur 3
                        </span>
                      </div>
                      <span className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-400 group-hover:-translate-y-1 group-hover:rotate-6">
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
                          <li
                            key={point}
                            className="flex items-start gap-2.5 text-sm text-[#1C2B1C]/80"
                          >
                            <span
                              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-transform duration-300 group-hover:scale-110"
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
                          "opacity-80 transition group-hover:opacity-100",
                        )}
                        style={{ color: step.accent }}
                      >
                        Ouvrir <ArrowRight className="nudge-target h-4 w-4" />
                      </span>
                    </div>
                  </Link>
                </Reveal>
              );
            })}
          </div>

          <Reveal delay={720} className="mt-10 flex justify-center">
            <Button
              asChild
              size="lg"
              className="press h-14 px-7 rounded-xl bg-[#2F5230] text-[#E7F0E8] hover:bg-[#264226] font-semibold transition-transform hover:-translate-y-0.5"
            >
              <Link to="/agriculture" className="nudge-x">
                Commencer par l’étape 1 - Agriculture
                <ArrowRight className="nudge-target ml-2 h-5 w-5" />
              </Link>
            </Button>
          </Reveal>
        </div>
      </section>

      <div className="landing-section-divider" aria-hidden />

      {/* Chiffres clés - bandeau vert foncé */}
      <section className="bg-[#2F5230] px-5 py-16 md:px-10 md:py-20 text-[#E7F0E8]">
        <Reveal className="mx-auto mb-10 max-w-2xl text-center">
          <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-white">
            AgriMent en chiffres
          </h2>
          <p className="mt-3 text-[#E7F0E8]/70">
            Des indicateurs concrets pour un conseil ancré dans le terrain.
          </p>
        </Reveal>
        <div className="mx-auto grid max-w-6xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((stat, i) => (
            <Reveal key={stat.label} from="scale" delay={120 + i * 140}>
              <StatTile {...stat} dark />
            </Reveal>
          ))}
        </div>
      </section>

      <div className="landing-section-divider" aria-hidden />

      {/* Matériel - fond sauge */}
      <section className="overflow-hidden bg-[#E7F0E8] px-0 py-16 md:py-20">
        <Reveal className="mx-auto mb-10 max-w-2xl px-5 text-center md:px-10">
          <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-[#2F5230]">
            Adapté à votre matériel
          </h2>
          <p className="mt-3 text-[#1C2B1C]/65">
            Déclarez vos équipements : nos scénarios ne recommandent que ce que vous pouvez
            réellement mettre en œuvre.
          </p>
        </Reveal>

        <Reveal delay={200} from="blur">
          <div className="marquee-mask marquee-pause">
            <div className="marquee-track gap-4" style={{ ["--marquee-duration" as string]: "46s" }}>
              {[...EQUIPEMENT_OPTIONS, ...EQUIPEMENT_OPTIONS].map((tool, i) => (
                <figure
                  key={`${tool.value}-${i}`}
                  className="group relative h-52 w-72 shrink-0 overflow-hidden rounded-2xl bg-white shadow-[0_8px_30px_-18px_rgba(28,43,28,0.35)] ring-1 ring-[#1C2B1C]/08"
                  aria-hidden={i >= EQUIPEMENT_OPTIONS.length}
                >
                  <img
                    src={tool.image}
                    alt={i < EQUIPEMENT_OPTIONS.length ? tool.label : ""}
                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                    loading="lazy"
                  />
                  <div
                    className="absolute inset-0"
                    style={{
                      background:
                        "linear-gradient(180deg, rgba(28,43,28,0) 40%, rgba(28,43,28,0.75) 100%)",
                    }}
                    aria-hidden
                  />
                  <figcaption className="absolute bottom-3 left-4 right-4 text-sm font-semibold text-white">
                    {tool.label}
                  </figcaption>
                </figure>
              ))}
            </div>
          </div>
        </Reveal>
      </section>

      {/* Closing CTA - carte blanche renforcée */}
      <section className="bg-[#E7F0E8] px-5 py-16 md:px-10 md:py-20">
        <Reveal from="blur" className="mx-auto max-w-5xl">
          <div className="overflow-hidden rounded-3xl border border-[#1C2B1C]/10 bg-white shadow-[0_18px_50px_-30px_rgba(28,43,28,0.4)]">
            <div className="h-1.5 w-full bg-[#E8C04A]" aria-hidden />
            <div className="flex flex-col gap-6 px-7 py-8 md:flex-row md:items-center md:justify-between md:px-10 md:py-10">
              <div className="max-w-xl">
                <h2 className="font-display text-2xl md:text-3xl font-semibold tracking-tight text-[#1C2B1C]">
                  Prêt à regarder votre parcelle autrement&nbsp;?
                </h2>
                <p className="mt-2 text-[#1C2B1C]/60">
                  Créez votre compte et lancez votre première analyse de terrain.
                </p>
              </div>
              <Button
                asChild
                size="lg"
                className="press h-14 shrink-0 rounded-full bg-[#2F5230] px-8 text-base font-semibold text-white hover:bg-[#264226] transition-transform hover:-translate-y-0.5"
              >
                <Link to="/inscription" className="nudge-x">
                  Rejoindre AgriMent <ArrowRight className="nudge-target ml-2 h-5 w-5" />
                </Link>
              </Button>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Footer */}
      <footer className="mt-auto bg-[#1C2B1C] text-[#E7F0E8]">
        <div className="mx-auto max-w-5xl px-5 py-12 md:px-10">
          <Reveal from="up" className="flex flex-col gap-10 md:flex-row md:justify-between">
            <div>
              <AgriLogo size={44} withWordmark tagline="Conseil de terrain" variant="onDark" />
              <p className="mt-4 max-w-xs text-sm text-[#E7F0E8]/55 leading-relaxed">
                Plateforme de conseil agricole : cultures, budget et réglementation - du sol aux
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
          </Reveal>

          <div className="mt-12 border-t border-white/10 pt-8">
            <Reveal>
              <div className="text-xs font-semibold tracking-[0.18em] uppercase text-[#E7F0E8]/40">
                Sources & références
              </div>
              <p className="mt-2 max-w-2xl text-sm text-[#E7F0E8]/50">
                AgriMent s’appuie sur des données et référentiels publics pour ses analyses de marché
                et son conseil réglementaire.
              </p>
            </Reveal>
            <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {REFERENCES.map((ref, i) => (
                <Reveal key={ref.name} as="li" from="scale" delay={100 + i * 100}>
                  <a
                    href={ref.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex h-24 flex-col items-center justify-center gap-1.5 rounded-xl bg-white px-3 py-3 transition-all duration-300 hover:-translate-y-1 hover:ring-2 hover:ring-[#D4F07A]/60"
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
                </Reveal>
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

function StatTile({
  value,
  suffix,
  label,
  sub,
  dark = false,
}: {
  value: number;
  suffix: string;
  label: string;
  sub: string;
  dark?: boolean;
}) {
  const [ref, displayed] = useCountUp(value);
  return (
    <div
      className={cn(
        "hover-lift rounded-2xl p-6 shadow-[0_8px_30px_-20px_rgba(28,43,28,0.35)]",
        dark
          ? "bg-white/10 ring-1 ring-white/15 backdrop-blur-sm"
          : "bg-white ring-1 ring-[#1C2B1C]/08",
      )}
    >
      <div
        className={cn(
          "font-display text-4xl font-semibold tracking-tight",
          dark ? "text-[#D4F07A]" : "text-[#2F5230]",
        )}
      >
        <span ref={ref}>{displayed}</span>
        {suffix}
      </div>
      <div className={cn("mt-1 text-sm font-semibold", dark ? "text-white" : "text-[#1C2B1C]")}>
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-xs leading-relaxed",
          dark ? "text-[#E7F0E8]/65" : "text-[#1C2B1C]/55",
        )}
      >
        {sub}
      </div>
    </div>
  );
}
