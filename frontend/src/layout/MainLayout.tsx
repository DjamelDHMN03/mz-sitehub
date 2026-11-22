import { Outlet, useLocation, Navigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Navbar } from "./Navbar";
import { useAuth } from "@/lib/auth";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/sites": "Sites",
  "/carte": "Carte",
  "/negociateurs": "N\u00e9gociateurs",
  "/carte/importer": "Importer KMZ/KML",
  "/contacts": "Contacts",
  "/documents": "Documents",
  "/doc-b": "Doc B",
  "/aps": "APS / Plans",
  "/contrats": "Contrats",
  "/actions": "Actions",
  "/kanban": "Kanban",
  "/calendrier": "Calendrier",
  "/rapports": "Rapports",
  "/historique": "Historique",
  "/assistant": "MZ Assistant",
  "/equipe": "\u00c9quipe",
  "/corbeille": "Corbeille",
  "/utilisateurs": "Utilisateurs",
  "/parametres": "Paramètres",
};

export function MainLayout() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center text-mz-text-muted">Chargement...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen bg-mz-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Navbar title={TITLES[location.pathname] ?? (location.pathname.startsWith("/sites/") ? "Fiche site" : "MZ BUILDING")} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
