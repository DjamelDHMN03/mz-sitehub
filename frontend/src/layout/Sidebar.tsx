import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, MapPin, Map, Users, FileText, ClipboardList,
  Ruler, FileSignature, CheckSquare, Calendar, BarChart3, Zap, Bot,
  History, Trash2, UserCog, Settings, UserCheck, MessageCircle,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/sites", label: "Sites", icon: MapPin },
  { to: "/carte", label: "Carte", icon: Map },
  { to: "/negociateurs", label: "N\u00e9gociateurs", icon: UserCheck },
  { to: "/contacts", label: "Contacts", icon: Users },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/doc-b", label: "Doc B", icon: ClipboardList },
  { to: "/aps", label: "APS / Plans", icon: Ruler },
  { to: "/contrats", label: "Contrats", icon: FileSignature },
  { to: "/energie", label: "Énergie", icon: Zap },
  { to: "/actions", label: "Actions", icon: CheckSquare },
  { to: "/calendrier", label: "Calendrier", icon: Calendar },
  { to: "/rapports", label: "Rapports", icon: BarChart3 },
  { to: "/assistant", label: "MZ Assistant", icon: Bot },
  { to: "/equipe", label: "\u00c9quipe", icon: MessageCircle },
  { to: "/historique", label: "Historique", icon: History },
  { to: "/corbeille", label: "Corbeille", icon: Trash2 },
  { to: "/utilisateurs", label: "Utilisateurs", icon: UserCog },
  { to: "/parametres", label: "ParamÃ¨tres", icon: Settings },
] as const;

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-mz-border bg-mz-surface">
      <div className="flex items-center gap-3 px-5 py-5 border-b border-mz-border">
        <img src="/logo-mz-building.png" alt="MZ Building" className="h-8 w-auto" />
        <div className="leading-tight">
          <p className="text-sm font-semibold text-mz-text">MZ BUILDING</p>
          <p className="text-xs text-mz-text-muted">Acquisition &amp; Project Management</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-mz-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-mz-primary/15 text-mz-primary font-medium"
                  : "text-mz-text-muted hover:bg-mz-surface-2 hover:text-mz-text"
              )
            }
          >
            <Icon size={17} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center gap-2 border-t border-mz-border px-5 py-3">
        <img src="/logo-ooredoo.png" alt="Ooredoo" className="h-5 w-auto opacity-80" />
        <span className="text-xs text-mz-text-disabled">Partenaire rÃ©seau</span>
      </div>
    </aside>
  );
}

