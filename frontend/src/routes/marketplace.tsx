import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { Plus, Store } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/marketplace")({
  head: () => ({
    meta: [
      { title: "Marketplace — AgriGuide" },
      {
        name: "description",
        content: "Achetez, vendez et échangez récoltes et déchets valorisables entre agriculteurs.",
      },
      { property: "og:title", content: "Marketplace — AgriGuide" },
      {
        property: "og:description",
        content: "Un marché communautaire pour vos récoltes et vos déchets valorisables.",
      },
    ],
  }),
  component: Layout,
});

const tabs = [
  { to: "/marketplace" as const, label: "Parcourir", exact: true },
  { to: "/marketplace/mes-annonces" as const, label: "Mes annonces" },
];

function Layout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAcheteur = user?.role === "acheteur";
  const showTabs =
    (!pathname.startsWith("/marketplace/nouveau") && !/^\/marketplace\/[^/]+$/.test(pathname)) ||
    pathname === "/marketplace" ||
    pathname === "/marketplace/mes-annonces";

  // Un acheteur peut parcourir et consulter le détail d'une annonce, mais ne
  // peut ni déposer d'annonce ni gérer "mes annonces" (il n'en a pas).
  const restrictedForAcheteur =
    pathname.startsWith("/marketplace/nouveau") || pathname.startsWith("/marketplace/mes-annonces");
  useEffect(() => {
    if (isAcheteur && restrictedForAcheteur) {
      navigate({ to: "/marketplace" });
    }
  }, [isAcheteur, restrictedForAcheteur, navigate]);

  return (
    <AppShell allowRoles={["farmer", "acheteur"]}>
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
            <Store className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">
              Marketplace
            </h1>
            <p className="text-muted-foreground mt-1">
              Récoltes & déchets valorisables — entre agriculteurs.
            </p>
          </div>
        </div>
        {!isAcheteur && (
          <Link
            to="/marketplace/nouveau"
            className="inline-flex items-center gap-2 rounded-2xl bg-primary text-primary-foreground px-5 h-12 font-medium shadow-soft hover:bg-primary/90"
          >
            <Plus className="h-5 w-5" /> Déposer une annonce
          </Link>
        )}
      </div>

      {showTabs && !isAcheteur && (
        <div className="flex gap-2 mb-6 border-b border-border">
          {tabs.map((t) => {
            const active = t.exact ? pathname === t.to : pathname.startsWith(t.to);
            return (
              <Link
                key={t.to}
                to={t.to}
                className={cn(
                  "px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors",
                  active
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {t.label}
              </Link>
            );
          })}
        </div>
      )}

      {isAcheteur && restrictedForAcheteur ? null : <Outlet />}
    </AppShell>
  );
}
