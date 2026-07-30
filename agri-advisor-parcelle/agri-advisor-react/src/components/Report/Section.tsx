import type { ReactNode } from "react";

interface SectionProps {
  icon: string;
  iconClass: string;
  title: string;
  subtitle?: string;
  warn?: boolean;
  children: ReactNode;
}

export function Section({ icon, iconClass, title, subtitle, warn, children }: SectionProps) {
  return (
    <div className={`rsec${warn ? " rsec-warn" : ""}`}>
      <div className="rsh">
        <div className={`sico ${iconClass}`}>{icon}</div>
        <div>
          <div className="stit">{title}</div>
          {subtitle && <div className="ssub">{subtitle}</div>}
        </div>
      </div>
      {children}
    </div>
  );
}
