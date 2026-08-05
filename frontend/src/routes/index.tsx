import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, ArrowUpRight, LineChart, ScrollText, Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgriLogo } from "@/components/AgriLogo";
import { Reveal } from "@/components/motion/Reveal";
import { HeroMedia } from "@/components/motion/HeroMedia";
import { useCountUp } from "@/components/motion/useCountUp";
import { EQUIPEMENT_OPTIONS } from "@/lib/equipements";

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

const JOURNEY = [
  {
    to: "/agriculture" as const,
    step: "01",
    title: "Agricole",
    body: "Sol, climat, auxiliaires — les cultures qui collent à votre parcelle.",
    image: "/img/journey/agriculture.jpg",
    icon: Sprout,
  },
  {
    to: "/business" as const,
    step: "02",
    title: "Business",
    body: "Trois scénarios chiffrés : profit, risque, hectares alloués.",
    image: "/img/journey/business.jpg",
    icon: LineChart,
  },
  {
    to: "/regulation" as const,
    step: "03",
    title: "Réglementaire",
    body: "Aides, certifications et cadre légal — sans jargon.",
    image: "/img/journey/regulation.jpg",
    icon: ScrollText,
  },
] as const;

const HERO_IMAGE = "/img/landing-hero-field.jpg?v=2";
const HERO_VIDEO = "/video/LandingPage.mp4";

const STATS = [
  { value: 3, suffix: "", label: "conseillers IA", sub: "Agricole, business, réglementaire" },
  { value: 5, suffix: "", label: "cultures classées", sub: "Par parcelle analysée" },
  { value: 800, suffix: " m", label: "rayon voisinage", sub: "Contexte cultural réel" },
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
    <div className="landing-page relative min-h-screen w-full overflow-x-hidden bg-[#0f1c18] text-[#e8f2ec] flex flex-col">
      {/* Hero — full-bleed, brand-first, one job */}
      <section className="relative isolate h-[100svh] min-h-[560px] w-full overflow-hidden">
        <HeroMedia
          poster={HERO_IMAGE}
          videoSrc={HERO_VIDEO}
          alt="Champ agricole en mouvement"
          objectPosition="center 40%"
          soften
        />
        <div
          className="pointer-events-none absolute inset-0 z-[2]"
          style={{
            background:
              "linear-gradient(180deg, rgba(15,28,24,0.35) 0%, rgba(15,28,24,0.12) 38%, rgba(15,28,24,0.62) 100%)",
          }}
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 z-[2] h-40"
          style={{
            background: "linear-gradient(180deg, transparent, rgba(15,28,24,0.92))",
          }}
          aria-hidden
        />

        <header className="relative z-10 flex items-center justify-between gap-4 px-5 pt-7 md:px-10 md:pt-9">
          <AgriLogo
            size={42}
            withWordmark
            tagline={null}
            className="landing-rise [&_span]:!text-white [&_.text-primary]:!text-signal"
          />
          <Link
            to="/connexion"
            className="landing-rise landing-rise-delay-1 text-sm font-semibold text-white/85 transition hover:text-white"
          >
            Connexion
          </Link>
        </header>

        <div className="relative z-10 flex min-h-[calc(100svh-5.5rem)] flex-col justify-end px-5 pb-16 pt-24 md:px-10 md:pb-20">
          <div className="max-w-3xl">
            <h1 className="landing-rise font-display text-[clamp(2.4rem,6.5vw,4.5rem)] font-extrabold leading-[1.02] tracking-tight text-white">
              Cultiver un monde{" "}
              <span className="text-signal">plus prévisible</span>,{" "}
              <span className="text-signal">plus rentable</span>.
            </h1>
            <p className="landing-rise landing-rise-delay-1 mt-5 max-w-xl text-base md:text-lg text-white/75 leading-relaxed">
              AgriMent relie analyse de parcelle, scénarios budgétaires et aides réglementaires —
              trois conseillers IA pour décider clairement, du sol au bilan.
            </p>
            <div className="landing-rise landing-rise-delay-2 mt-8 flex flex-col sm:flex-row gap-3">
              <Button
                asChild
                size="lg"
                className="press h-12 px-8 text-base rounded-xl bg-signal text-signal-foreground hover:bg-[#d4f55a] font-bold shadow-none"
              >
                <Link to="/inscription" className="nudge-x">
                  Commencer <ArrowRight className="nudge-target ml-1 h-5 w-5" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-12 px-7 text-base rounded-xl border-white/25 bg-transparent text-white hover:bg-white/10 hover:text-white"
              >
                <Link to="/connexion">Se connecter</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Flow — horizontal signal, not presentation cards */}
      <section className="relative bg-[#0f1c18] px-5 py-20 md:px-10 md:py-28">
        <div className="mx-auto max-w-6xl">
          <Reveal className="max-w-xl">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/80">
              Parcours
            </p>
            <h2 className="mt-3 font-display text-3xl md:text-5xl font-bold tracking-tight text-white leading-[1.05]">
              Trois signaux.
              <br />
              Une décision.
            </h2>
          </Reveal>

          <div className="relative mt-14">
            <div
              className="pointer-events-none absolute left-0 right-0 top-[1.15rem] hidden h-px md:block"
              style={{
                background:
                  "linear-gradient(90deg, transparent, oklch(0.88 0.18 125 / 0.55), transparent)",
              }}
              aria-hidden
            />
            <ol className="grid gap-8 md:grid-cols-3 md:gap-6">
              {JOURNEY.map((step, i) => {
                const Icon = step.icon;
                return (
                  <Reveal key={step.to} as="li" from="up" delay={i * 120}>
                    <Link
                      to={step.to}
                      className="group relative flex flex-col gap-5 outline-none"
                    >
                      <div className="relative z-10 flex h-9 w-9 items-center justify-center rounded-full border border-signal/40 bg-[#0f1c18] font-mono text-xs font-semibold text-signal transition-transform duration-300 group-hover:scale-110">
                        {step.step}
                      </div>
                      <div className="relative overflow-hidden rounded-2xl aspect-[5/3]">
                        <img
                          src={step.image}
                          alt=""
                          className="h-full w-full object-cover transition duration-700 group-hover:scale-105"
                          loading="lazy"
                        />
                        <div
                          className="absolute inset-0"
                          style={{
                            background:
                              "linear-gradient(180deg, transparent 30%, rgba(15,28,24,0.85) 100%)",
                          }}
                          aria-hidden
                        />
                        <Icon className="absolute bottom-3 right-3 h-5 w-5 text-signal" />
                      </div>
                      <div>
                        <h3 className="font-display text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                          {step.title}
                          <ArrowUpRight className="h-4 w-4 text-signal opacity-0 -translate-y-1 translate-x-1 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-0 group-hover:translate-y-0" />
                        </h3>
                        <p className="mt-2 text-sm leading-relaxed text-white/55">{step.body}</p>
                      </div>
                    </Link>
                  </Reveal>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      <div className="landing-section-divider" aria-hidden />

      {/* Stats — typographic, not tiles in a grid of cards */}
      <section className="bg-[#142621] px-5 py-16 md:px-10 md:py-24">
        <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1fr_1.4fr] md:items-end">
          <Reveal>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/80">
              Ancré terrain
            </p>
            <h2 className="mt-3 font-display text-3xl md:text-4xl font-bold tracking-tight text-white">
              Des chiffres utiles, pas du décor.
            </h2>
          </Reveal>
          <div className="grid gap-8 sm:grid-cols-2">
            {STATS.map((stat, i) => (
              <Reveal key={stat.label} from="up" delay={80 + i * 80}>
                <StatLine {...stat} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Matériel — full-bleed strip */}
      <section className="overflow-hidden bg-[#0f1c18] py-16 md:py-20">
        <Reveal className="mx-auto mb-10 max-w-2xl px-5 text-center md:px-10">
          <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-white">
            Adapté à votre matériel
          </h2>
          <p className="mt-3 text-white/55">
            Vos équipements filtrent les scénarios — rien d’irréaliste.
          </p>
        </Reveal>

        <Reveal delay={160} from="blur">
          <div className="marquee-mask marquee-pause">
            <div className="marquee-track gap-3" style={{ ["--marquee-duration" as string]: "46s" }}>
              {[...EQUIPEMENT_OPTIONS, ...EQUIPEMENT_OPTIONS].map((tool, i) => (
                <figure
                  key={`${tool.value}-${i}`}
                  className="group relative h-48 w-64 shrink-0 overflow-hidden rounded-xl"
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
                        "linear-gradient(180deg, rgba(15,28,24,0) 35%, rgba(15,28,24,0.9) 100%)",
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

      {/* Closing CTA */}
      <section className="relative overflow-hidden bg-signal px-5 py-16 md:px-10 md:py-20 text-signal-foreground">
        <div
          className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-white/20 blur-3xl"
          aria-hidden
        />
        <Reveal className="relative mx-auto flex max-w-5xl flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="max-w-xl">
            <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight">
              Prêt à regarder votre parcelle autrement&nbsp;?
            </h2>
            <p className="mt-2 text-signal-foreground/70">
              Créez votre compte et lancez la première analyse.
            </p>
          </div>
          <Button
            asChild
            size="lg"
            className="press h-12 shrink-0 rounded-xl bg-[#0f1c18] px-8 text-base font-bold text-white hover:bg-[#163028]"
          >
            <Link to="/inscription" className="nudge-x">
              Rejoindre AgriMent <ArrowRight className="nudge-target ml-1 h-5 w-5" />
            </Link>
          </Button>
        </Reveal>
      </section>

      <footer className="mt-auto bg-[#0a1411] text-[#e8f2ec]">
        <div className="mx-auto max-w-5xl px-5 py-12 md:px-10">
          <Reveal from="up" className="flex flex-col gap-10 md:flex-row md:justify-between">
            <div>
              <AgriLogo size={44} withWordmark tagline="Conseil de terrain" variant="onDark" />
              <p className="mt-4 max-w-xs text-sm text-white/45 leading-relaxed">
                Cultures, budget et réglementation — du sol aux insectes du champ.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-10 sm:gap-16">
              <div>
                <div className="font-mono text-[10px] font-semibold tracking-[0.18em] uppercase text-white/35">
                  Compte
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  <li>
                    <Link to="/inscription" className="text-white/75 hover:text-white">
                      Créer un compte
                    </Link>
                  </li>
                  <li>
                    <Link to="/connexion" className="text-white/75 hover:text-white">
                      Se connecter
                    </Link>
                  </li>
                </ul>
              </div>
              <div>
                <div className="font-mono text-[10px] font-semibold tracking-[0.18em] uppercase text-white/35">
                  Conseillers
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  {JOURNEY.map((f) => (
                    <li key={f.to}>
                      <Link to={f.to} className="text-white/75 hover:text-white">
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
              <div className="font-mono text-[10px] font-semibold tracking-[0.18em] uppercase text-white/35">
                Sources & références
              </div>
            </Reveal>
            <ul className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {REFERENCES.map((ref, i) => (
                <Reveal key={ref.name} as="li" from="scale" delay={80 + i * 80}>
                  <a
                    href={ref.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex h-20 flex-col items-center justify-center gap-1 rounded-xl bg-white px-3 py-2 transition-transform duration-300 hover:-translate-y-0.5"
                    title={`Ouvrir ${ref.name}`}
                  >
                    <img
                      src={ref.src}
                      alt={ref.name}
                      className="max-h-10 w-auto max-w-full object-contain"
                      loading="lazy"
                    />
                    <span className="text-[10px] font-medium text-[#1C2B1C]/55">{ref.name}</span>
                  </a>
                </Reveal>
              ))}
            </ul>
          </div>

          <div className="mt-10 flex flex-col gap-2 border-t border-white/10 pt-6 text-xs text-white/35 sm:flex-row sm:items-center sm:justify-between">
            <span>© {new Date().getFullYear()} AgriMent. Tous droits réservés.</span>
            <span>Construit avec Mistral</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function StatLine({
  value,
  suffix,
  label,
  sub,
}: {
  value: number;
  suffix: string;
  label: string;
  sub: string;
}) {
  const [ref, displayed] = useCountUp(value);
  return (
    <div className="border-t border-white/10 pt-4">
      <div className="font-display text-4xl md:text-5xl font-bold tracking-tight text-signal">
        <span ref={ref}>{displayed}</span>
        {suffix}
      </div>
      <div className="mt-1 text-sm font-semibold text-white">{label}</div>
      <div className="mt-0.5 text-xs text-white/45">{sub}</div>
    </div>
  );
}
