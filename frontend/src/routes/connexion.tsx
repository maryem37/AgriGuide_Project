import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { AuthLayout } from "@/components/AuthLayout";
import { AlertBanner } from "@/components/AlertBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { AuthApiError } from "@/lib/authApi";

export const Route = createFileRoute("/connexion")({
  head: () => ({
    meta: [
      { title: "Se connecter - AgriMent" },
      { name: "description", content: "Connectez-vous à votre compte AgriMent." },
    ],
  }),
  component: Page,
});

function Page() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await signIn({ email, password });
      navigate({ to: user.role === "farmer" ? "/dashboard" : "/marketplace" });
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Une erreur inattendue est survenue.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Se connecter" subtitle="Retrouvez votre exploitation et vos conseillers.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1.5 h-11 rounded-xl"
          />
        </div>
        <div>
          <Label htmlFor="password">Mot de passe</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="mt-1.5 h-11 rounded-xl"
          />
        </div>

        {error && (
          <AlertBanner tone="danger" title="Connexion impossible">
            {error}
          </AlertBanner>
        )}

        <Button type="submit" disabled={submitting} className="w-full h-12 rounded-xl mt-2">
          {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Se connecter
          {!submitting && <ArrowRight className="h-4 w-4 ml-2" />}
        </Button>
      </form>

      <p className="text-sm text-center text-muted-foreground mt-8">
        Pas encore de compte ?{" "}
        <Link to="/inscription" className="text-primary font-medium underline underline-offset-4">
          Créer un compte
        </Link>
      </p>
    </AuthLayout>
  );
}
