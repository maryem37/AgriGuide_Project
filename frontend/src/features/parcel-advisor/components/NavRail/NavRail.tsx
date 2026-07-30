import "./NavRail.css";

export type AppView = "carte" | "agriculture";

interface NavItem {
  id: AppView | "soon";
  key: string;
  icon: string;
  label: string;
  enabled: boolean;
}

const ITEMS: NavItem[] = [
  { id: "soon", key: "dashboard", icon: "📊", label: "Tableau de bord", enabled: false },
  { id: "agriculture", key: "agriculture", icon: "🌱", label: "Agriculture", enabled: true },
  { id: "soon", key: "reglementation", icon: "📜", label: "Réglementation", enabled: false },
  { id: "soon", key: "business", icon: "💼", label: "Business", enabled: false },
  { id: "soon", key: "suivi", icon: "🗓️", label: "Suivi quotidien", enabled: false },
  { id: "soon", key: "marketplace", icon: "🛒", label: "Marketplace", enabled: false },
];

interface NavRailProps {
  active: AppView;
  onSelect: (view: AppView) => void;
}

export function NavRail({ active, onSelect }: NavRailProps) {
  return (
    <nav className="navrail">
      <div className="navrail-brand">
        <div className="bicon">🌾</div>
        <div>
          <h1>Agri Advisor IA</h1>
          <p>Conseiller agronomique</p>
        </div>
      </div>

      <div className="navrail-items">
        {ITEMS.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.key}
              className={`navrail-item${isActive ? " active" : ""}${!item.enabled ? " disabled" : ""}`}
              onClick={() => item.enabled && onSelect(item.id as AppView)}
              disabled={!item.enabled}
              title={item.enabled ? undefined : "Bientôt disponible"}
            >
              <span className="navrail-icon">{item.icon}</span>
              <span className="navrail-label">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
