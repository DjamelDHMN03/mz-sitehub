import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { MainLayout } from "@/layout/MainLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SitesPage from "@/pages/SitesPage";
import CartePage from "@/pages/CartePage";
import NegociateursPage from "@/pages/NegociateursPage";
import ImportCartePage from "@/pages/ImportCartePage";
import ContactsPage from "@/pages/ContactsPage";
import DocumentsPage from "@/pages/DocumentsPage";
import DocBApsPage from "@/pages/DocBApsPage";
import ContractsPage from "@/pages/ContractsPage";
import EnergiePage from "@/pages/EnergiePage";
import ActionsPage from "@/pages/ActionsPage";
import KanbanPage from "@/pages/KanbanPage";
import CalendrierPage from "@/pages/CalendrierPage";
import SharePage from "@/pages/SharePage";
import ImportExcelPage from "@/pages/ImportExcelPage";
import RapportsPage from "@/pages/RapportsPage";
import HistoriquePage from "@/pages/HistoriquePage";
import AssistantPage from "@/pages/AssistantPage";
import ChatPage from "@/pages/ChatPage";
import TrashPage from "@/pages/TrashPage";
import UsersPage from "@/pages/UsersPage";
import SettingsPage from "@/pages/SettingsPage";
import SiteDetailPage from "@/pages/SiteDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/share/:token" element={<SharePage />} />
          <Route element={<MainLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/sites" element={<SitesPage />} />
            <Route path="/sites/:id" element={<SiteDetailPage />} />
            <Route path="/carte" element={<CartePage />} />
          <Route path="/negociateurs" element={<NegociateursPage />} />
            <Route path="/carte/importer" element={<ImportCartePage />} />
            <Route path="/contacts" element={<ContactsPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/doc-b" element={<DocBApsPage />} />
            <Route path="/aps" element={<DocBApsPage />} />
            <Route path="/contrats" element={<ContractsPage />} />
            <Route path="/energie" element={<EnergiePage />} />
            <Route path="/actions" element={<ActionsPage />} />
            <Route path="/kanban" element={<KanbanPage />} />
            <Route path="/calendrier" element={<CalendrierPage />} />
            <Route path="/sites/importer-excel" element={<ImportExcelPage />} />
            <Route path="/rapports" element={<RapportsPage />} />
            <Route path="/historique" element={<HistoriquePage />} />
            <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/equipe" element={<ChatPage />} />
            <Route path="/corbeille" element={<TrashPage />} />
            <Route path="/utilisateurs" element={<UsersPage />} />
            <Route path="/parametres" element={<SettingsPage />} />
            {/* Les autres routes de la Sidebar (carte, contacts, documents...)
                seront ajoutÃ©es phase par phase, au fur et Ã  mesure de leur
                construction â€” pas de pages vides crÃ©Ã©es Ã  l'avance. */}
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}


