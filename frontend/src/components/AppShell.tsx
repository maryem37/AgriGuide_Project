import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Home,
  Sprout,
  ScrollText,
  LineChart,
  CalendarDays,
  Store,
  LogOut,
  User,
  Loader2,
} from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useAuth, roleLabel } from "@/lib/auth-context";
import type { Role } from "@/lib/authApi";
import { AgriLogo } from "@/components/AgriLogo";
import { ScrollMoreHint } from "@/components/motion/ScrollMoreHint";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const nav = [
  { to: "/dashboard", label: "Accueil", icon: Home, roles: ["farmer"] as Role[] },
  { to: "/agriculture", label: "Cultures", icon: Sprout, roles: ["farmer"] as Role[] },
  { to: "/regulation", label: "Règles", icon: ScrollText, roles: ["farmer"] as Role[] },
  { to: "/business", label: "Budget", icon: LineChart, roles: ["farmer"] as Role[] },
  { to: "/aujourd-hui", label: "Aujourd'hui", icon: CalendarDays, roles: ["farmer"] as Role[] },
  { to: "/marketplace", label: "Marché", icon: Store, roles: ["farmer", "acheteur"] as Role[] },
] as const;

function FullPageLoader() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background">
      <span className="relative flex h-12 w-12 items-center justify-center rounded-full text-primary pulse-ring">
        <Loader2 className="h-7 w-7 animate-spin" />
      </span>
      <span className="text-sm text-muted-foreground">Chargement…</span>
    </div>
  );
}

export function AppShell({
  children,
  allowRoles = ["farmer"],
}: {
  children: ReactNode;
  allowRoles?: Role[];
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { status, user, signOut } = useAuth();
  const navigate = useNavigate();

  const roleMismatch =
    status === "authenticated" && user !== null && !allowRoles.includes(user.role);

  useEffect(() => {
    if (status === "anonymous") {
      navigate({ to: "/connexion" });
    } else if (roleMismatch && user) {
      navigate({ to: user.role === "farmer" ? "/dashboard" : "/marketplace" });
    }
  }, [status, roleMismatch, user, navigate]);

  if (status === "loading" || status === "anonymous" || roleMismatch) {
    return <FullPageLoader />;
  }

  const visibleNav = nav.filter((n) => !user || n.roles.includes(user.role));

  return (
    <div className="app-motion min-h-screen bg-background pb-24 md:pb-0 md:pl-72">
      {/* Sidebar (desktop) */}
      <aside className="hidden md:flex fixed left-0 top-0 h-screen w-72 flex-col border-r border-border bg-card px-6 py-8 gap-2">
        <Link to="/dashboard" className="mb-8 inline-flex press">
          <AgriLogo withWordmark size={44} tagline="Votre allié au quotidien" />
        </Link>
        <nav className="flex flex-col gap-1">
          {visibleNav.map(({ to, label, icon: Icon }, i) => {
            const active = pathname === to || pathname.startsWith(to + "/");
            return (
              <Link
                key={to}
                to={to}
                style={{ ["--i" as string]: i }}
                className={cn(
                  "group page-enter relative flex items-center gap-3 overflow-hidden rounded-xl px-4 py-3 text-base font-medium",
                  "transition-all duration-300 [animation-delay:calc(60ms*var(--i))]",
                  active
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-foreground hover:bg-secondary hover:translate-x-1",
                )}
              >
                {/* Liseré animé sur l'entrée active. */}
                <span
                  className={cn(
                    "absolute left-0 top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-full bg-[#fa520f]",
                    "origin-center transition-transform duration-300",
                    active ? "scale-y-100" : "scale-y-0",
                  )}
                  aria-hidden
                />
                <Icon
                  className={cn(
                    "h-5 w-5 transition-transform duration-300",
                    active ? "scale-110" : "group-hover:scale-110",
                  )}
                />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto">
          <UserMenu />
        </div>
      </aside>

      {/* `key` sur le pathname : chaque navigation rejoue l'animation d'entrée. */}
      <main key={pathname} className="page-enter mx-auto max-w-6xl px-4 py-6 md:px-10 md:py-10">
        {children}
        {pathname !== "/regulation" && !pathname.startsWith("/regulation/") && (
          <ScrollMoreHint />
        )}
      </main>

      {/* Bottom nav (mobile) */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-card/95 backdrop-blur border-t border-border">
        <div
          className="grid"
          style={{ gridTemplateColumns: `repeat(${visibleNav.length + 1}, minmax(0, 1fr))` }}
        >
          {visibleNav.map(({ to, label, icon: Icon }) => {
            const active = pathname === to || pathname.startsWith(to + "/");
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "press relative flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors duration-300",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "absolute top-0 h-0.5 w-8 rounded-full bg-primary transition-transform duration-300",
                    active ? "scale-x-100" : "scale-x-0",
                  )}
                  aria-hidden
                />
                <Icon
                  className={cn(
                    "h-5 w-5 transition-transform duration-300",
                    active && "-translate-y-0.5 scale-110",
                  )}
                />
                {label}
              </Link>
            );
          })}
          <UserMenu compact />
        </div>
      </nav>
    </div>
  );
}

function UserMenu({ compact = false }: { compact?: boolean }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const initiales = user.nom
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  function handleSignOut() {
    signOut();
    navigate({ to: "/connexion" });
  }

  if (compact) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger className="flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium text-muted-foreground">
          <Avatar className="h-5 w-5">
            <AvatarFallback className="text-[9px]">{initiales}</AvatarFallback>
          </Avatar>
          Profil
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="top">
          <DropdownMenuLabel className="truncate">{user.nom}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {user.role === "farmer" && (
            <DropdownMenuItem asChild>
              <Link to="/profil">
                <User className="h-4 w-4" /> Mon profil
              </Link>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={handleSignOut}>
            <LogOut className="h-4 w-4" /> Déconnexion
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-secondary transition-colors w-full">
        <Avatar className="h-9 w-9">
          <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
            {initiales}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold truncate">{user.nom}</div>
          <div className="text-xs text-muted-foreground">{roleLabel(user.role)}</div>
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="w-56">
        <DropdownMenuLabel className="truncate">{user.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {user.role === "farmer" && (
          <DropdownMenuItem asChild>
            <Link to="/profil">
              <User className="h-4 w-4" /> Mon profil
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={handleSignOut}>
          <LogOut className="h-4 w-4" /> Déconnexion
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
