import { Link } from "@tanstack/react-router";
import { Leaf } from "lucide-react";
import type { ReactNode } from "react";

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
    <div className="min-h-screen bg-background">
      <div className={`mx-auto ${maxWidth} px-4 py-8 md:py-12`}>
        <Link to="/" className="inline-flex items-center gap-3 mb-8">
          <div className="h-11 w-11 rounded-2xl bg-gradient-hero flex items-center justify-center shadow-sm">
            <Leaf className="h-6 w-6 text-primary-foreground" />
          </div>
          <div className="font-display text-xl font-semibold">AgriGuide</div>
        </Link>
        <h1 className="font-display text-3xl md:text-4xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-2 text-muted-foreground">{subtitle}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </div>
  );
}
