import { AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function AlertBanner({
  tone = "info",
  title,
  children,
  action,
}: {
  tone?: "info" | "warning" | "success" | "danger";
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  const Icon =
    tone === "warning" || tone === "danger"
      ? AlertTriangle
      : tone === "success"
        ? CheckCircle2
        : Info;
  const styles =
    tone === "warning"
      ? "bg-waste/15 border-waste/40 text-waste-foreground"
      : tone === "danger"
        ? "bg-destructive/10 border-destructive/40 text-destructive"
        : tone === "success"
          ? "bg-harvest/15 border-harvest/40 text-foreground"
          : "bg-sky/20 border-sky/40 text-sky-foreground";

  return (
    <div
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
      className={cn(
        "page-enter group flex items-start gap-3 rounded-2xl border p-4 transition-shadow duration-300 hover:shadow-soft",
        styles,
      )}
    >
      {/* L'icône se pose avec un léger rebond, puis réagit au survol. */}
      <Icon
        className={cn(
          "mt-0.5 h-6 w-6 shrink-0 transition-transform duration-500 group-hover:scale-110",
          (tone === "danger" || tone === "warning") && "group-hover:rotate-6",
        )}
      />
      <div className="flex-1">
        <div className="font-semibold">{title}</div>
        {children && <div className="mt-1 text-sm opacity-90">{children}</div>}
      </div>
      {action}
    </div>
  );
}
