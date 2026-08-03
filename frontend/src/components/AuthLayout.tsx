import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { AgriLogo } from "@/components/AgriLogo";

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
        <Link to="/" className="mb-8 inline-flex">
          <AgriLogo withWordmark size={44} />
        </Link>
        <h1 className="font-display text-3xl md:text-4xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-2 text-muted-foreground">{subtitle}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </div>
  );
}
