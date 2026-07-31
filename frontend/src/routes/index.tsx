import { createFileRoute, Link } from "@tanstack/react-router";
import { Leaf, Sprout, ShieldCheck, LineChart, ArrowRight, Users, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AgriMent — Bienvenue" },
      {
        name: "description",
        content:
          "AgriMent, l'assistant qui aide chaque agriculteur à cultiver, gérer et vendre en toute simplicité.",
      },
      { property: "og:title", content: "AgriMent — Bienvenue" },
      {
        property: "og:description",
        content:
          "AgriMent, l'assistant qui aide chaque agriculteur à cultiver, gérer et vendre en toute simplicité.",
      },
    ],
  }),
  component: Welcome,
});

function Welcome() {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* subtle top pattern */}
      <div className="absolute inset-x-0 top-0 h-[520px] bg-gradient-hero opacity-95" aria-hidden />
      <div
        className="absolute inset-x-0 top-0 h-[520px] opacity-20"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 30%, oklch(0.99 0 0 / .4), transparent 45%), radial-gradient(circle at 80% 70%, oklch(0.99 0 0 / .3), transparent 40%)",
        }}
      />

      <div className="relative mx-auto max-w-6xl px-5 pt-8 md:pt-12">
        <div className="flex items-center gap-3 text-primary-foreground">
          <div className="h-11 w-11 rounded-2xl bg-primary-foreground/15 flex items-center justify-center backdrop-blur">
            <Leaf className="h-6 w-6" />
          </div>
          <div className="font-display text-xl font-semibold">AgriMent</div>
        </div>

        <div className="mt-14 md:mt-20 max-w-3xl text-primary-foreground">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary-foreground/15 backdrop-blur px-3 py-1.5 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5" /> Propulsé par l'intelligence artificielle
          </div>
          <h1 className="mt-5 font-display text-5xl md:text-6xl font-semibold leading-[1.05]">
            Bonjour, cultivons&nbsp;
            <span className="italic">ensemble</span>.
          </h1>
          <p className="mt-5 text-lg md:text-xl text-primary-foreground/90 max-w-2xl">
            AgriMent vous accompagne, du choix de vos cultures à la vente de votre récolte. Simple,
            clair, sans jargon — comme un conseiller de confiance à vos côtés.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <Button
              asChild
              size="lg"
              className="h-14 px-8 text-base rounded-2xl bg-primary-foreground text-primary hover:bg-primary-foreground/90"
            >
              <Link to="/inscription">
                Créer un compte <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-14 px-8 text-base rounded-2xl bg-transparent border-primary-foreground/40 text-primary-foreground hover:bg-primary-foreground/10"
            >
              <Link to="/connexion">Se connecter</Link>
            </Button>
          </div>
        </div>

        <div className="relative mt-16 md:mt-24 grid gap-4 md:grid-cols-4">
          {[
            {
              icon: Sprout,
              title: "Choisir ses cultures",
              text: "Analyse du sol, climat et rendement historique.",
            },
            {
              icon: ShieldCheck,
              title: "Comprendre les règles",
              text: "Aides, PAC et certifications expliquées simplement.",
            },
            {
              icon: LineChart,
              title: "Gérer au jour le jour",
              text: "Météo, alertes, budget et carnet de bord.",
            },
            {
              icon: Users,
              title: "Vendre et échanger",
              text: "Marketplace pour récoltes et déchets valorisables.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} className="card-soft p-5">
              <div className="h-11 w-11 rounded-xl bg-secondary flex items-center justify-center text-primary">
                <Icon className="h-6 w-6" />
              </div>
              <div className="mt-3 font-semibold">{title}</div>
              <p className="mt-1 text-sm text-muted-foreground leading-snug">{text}</p>
            </div>
          ))}
        </div>

        <p className="text-center mt-16 mb-10 text-sm text-muted-foreground">
          Déjà plus de 12 000 agriculteurs français cultivent avec AgriMent.
        </p>
      </div>
    </div>
  );
}
