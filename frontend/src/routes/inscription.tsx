import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, type ReactNode } from "react";
import { AuthLayout } from "@/components/AuthLayout";
import { EquipementPicker } from "@/components/EquipementPicker";
import { TerrainListEditor, type DraftTerrain } from "@/components/TerrainListEditor";
import { AlertBanner } from "@/components/AlertBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, ArrowRight, Loader2, ShoppingBag, Sprout } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { AuthApiError, type EquipementType, type Role } from "@/lib/authApi";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/inscription")({
  head: () => ({
    meta: [
      { title: "Créer un compte — AgriGuide" },
      { name: "description", content: "Créez votre compte agriculteur ou acheteur sur AgriGuide." },
    ],
  }),
  component: Page,
});

type Step = "role" | "compte" | "materiel" | "terrains";

function Page() {
  const navigate = useNavigate();
  const { signUp } = useAuth();

  const [step, setStep] = useState<Step>("role");
  const [role, setRole] = useState<Role | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");

  const [equipements, setEquipements] = useState<EquipementType[]>([]);
  const [terrains, setTerrains] = useState<DraftTerrain[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compteValid = useMemo(
    () =>
      email.includes("@") &&
      password.length >= 8 &&
      password === confirmPassword &&
      nom.trim().length > 0,
    [email, password, confirmPassword, nom],
  );

  function goToAccountStep(chosen: Role) {
    setRole(chosen);
    setStep("compte");
  }

  function handleAccountNext() {
    if (!compteValid || !role) return;
    if (role === "farmer") setStep("materiel");
    else void submit(role);
  }

  async function submit(finalRole: Role) {
    setSubmitting(true);
    setError(null);
    try {
      const user = await signUp({
        email,
        password,
        nom,
        telephone: telephone || undefined,
        role: finalRole,
        equipements: finalRole === "farmer" ? equipements : undefined,
        terrains:
          finalRole === "farmer"
            ? terrains.map((t) => ({ nom: t.nom, points: t.points }))
            : undefined,
      });
      navigate({ to: user.role === "farmer" ? "/dashboard" : "/marketplace" });
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Une erreur inattendue est survenue.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Créer un compte"
      subtitle="Rejoignez AgriGuide en tant qu'agriculteur ou acheteur."
      maxWidth={step === "terrains" ? "max-w-3xl" : "max-w-lg"}
    >
      {step === "role" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <RoleCard
            icon={Sprout}
            title="Je suis agriculteur"
            desc="Accès complet : conseillers cultures, business, réglementation, suivi et marketplace."
            onClick={() => goToAccountStep("farmer")}
          />
          <RoleCard
            icon={ShoppingBag}
            title="Je suis acheteur"
            desc="Parcourez le marketplace pour trouver récoltes et déchets valorisables."
            onClick={() => goToAccountStep("acheteur")}
          />
        </div>
      )}

      {step === "compte" && role && (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            handleAccountNext();
          }}
        >
          <StepHeader
            onBack={() => setStep("role")}
            label={role === "farmer" ? "Agriculteur" : "Acheteur"}
          />

          <Field label="Nom complet" htmlFor="nom">
            <Input
              id="nom"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              required
              className="h-11 rounded-xl"
            />
          </Field>
          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-11 rounded-xl"
            />
          </Field>
          <Field label="Téléphone (optionnel)" htmlFor="telephone">
            <Input
              id="telephone"
              value={telephone}
              onChange={(e) => setTelephone(e.target.value)}
              className="h-11 rounded-xl"
            />
          </Field>
          <Field label="Mot de passe (8 caractères min.)" htmlFor="password">
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="h-11 rounded-xl"
            />
          </Field>
          <Field label="Confirmer le mot de passe" htmlFor="confirm-password">
            <Input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="h-11 rounded-xl"
            />
            {confirmPassword.length > 0 && confirmPassword !== password && (
              <p className="text-xs text-destructive mt-1">
                Les mots de passe ne correspondent pas.
              </p>
            )}
          </Field>

          {error && (
            <AlertBanner tone="danger" title="Impossible de créer le compte">
              {error}
            </AlertBanner>
          )}

          <Button
            type="submit"
            disabled={!compteValid || submitting}
            className="w-full h-12 rounded-xl mt-2"
          >
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {role === "farmer" ? "Continuer" : "Créer mon compte"}
            {!submitting && <ArrowRight className="h-4 w-4 ml-2" />}
          </Button>
        </form>
      )}

      {step === "materiel" && (
        <div className="space-y-6">
          <StepHeader onBack={() => setStep("compte")} label="Votre matériel agricole" />
          <p className="text-sm text-muted-foreground -mt-4">
            Cochez le matériel que vous possédez (les images seront ajoutées prochainement).
            Modifiable à tout moment depuis votre profil.
          </p>
          <EquipementPicker selected={equipements} onChange={setEquipements} />
          <Button onClick={() => setStep("terrains")} className="w-full h-12 rounded-xl">
            Continuer <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      )}

      {step === "terrains" && (
        <div className="space-y-6">
          <StepHeader onBack={() => setStep("materiel")} label="Vos terrains" />
          <p className="text-sm text-muted-foreground -mt-4">
            Tracez le contour de chaque parcelle et donnez-lui un nom (ex. "Parcelle Nord"). Vous
            pourrez en ajouter, renommer ou supprimer plus tard depuis votre profil.
          </p>

          <TerrainListEditor terrains={terrains} onChange={setTerrains} />

          {error && (
            <AlertBanner tone="danger" title="Impossible de créer le compte">
              {error}
            </AlertBanner>
          )}

          <Button
            onClick={() => void submit("farmer")}
            disabled={terrains.length === 0 || submitting}
            className="w-full h-12 rounded-xl"
          >
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Créer mon compte
          </Button>
          {terrains.length === 0 && (
            <p className="text-xs text-center text-muted-foreground">
              Ajoutez au moins un terrain pour continuer.
            </p>
          )}
        </div>
      )}

      <p className="text-sm text-center text-muted-foreground mt-8">
        Déjà un compte ?{" "}
        <Link to="/connexion" className="text-primary font-medium underline underline-offset-4">
          Se connecter
        </Link>
      </p>
    </AuthLayout>
  );
}

function RoleCard({
  icon: Icon,
  title,
  desc,
  onClick,
}: {
  icon: typeof Sprout;
  title: string;
  desc: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "text-left rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/50 hover:card-lift",
      )}
    >
      <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
        <Icon className="h-6 w-6" />
      </div>
      <div className="mt-4 font-display text-lg font-semibold">{title}</div>
      <p className="text-sm text-muted-foreground mt-1">{desc}</p>
    </button>
  );
}

function StepHeader({ onBack, label }: { onBack: () => void; label: string }) {
  return (
    <div className="flex items-center gap-3 mb-2">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onBack}
        className="h-8 w-8 shrink-0"
      >
        <ArrowLeft className="h-4 w-4" />
      </Button>
      <span className="text-sm font-semibold text-primary">{label}</span>
    </div>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div>
      <Label htmlFor={htmlFor}>{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
