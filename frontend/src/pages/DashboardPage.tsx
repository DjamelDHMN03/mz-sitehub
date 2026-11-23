import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";

interface MetricValue {
  value: number;
  available: boolean;
  note?: string | null;
}

interface DashboardStats {
  total_sites: MetricValue;
  nouveaux: MetricValue;
  en_cours: MetricValue;
  negociation: MetricValue;
  bloques: MetricValue;
  signes: MetricValue;
  operationnels: MetricValue;
  refuses: MetricValue;
  a_relancer: MetricValue;
  contrats_a_signer: MetricValue;
  aps_en_attente: MetricValue;
  doc_b_manquants: MetricValue;
  dossiers_incomplets: MetricValue;
}

const GROUPS: {
  title: string;
  cards: { key: keyof DashboardStats; label: string; tone: string }[];
}[] = [
  {
    title: "Portefeuille",
    cards: [
      { key: "total_sites", label: "Total des sites", tone: "text-mz-primary" },
    ],
  },
  {
    title: "État des sites",
    cards: [
      { key: "nouveaux", label: "Nouveaux", tone: "text-mz-status-nouveau" },
      { key: "en_cours", label: "En cours", tone: "text-mz-status-en-cours" },
      { key: "negociation", label: "Négociation", tone: "text-mz-status-attente" },
      { key: "bloques", label: "Bloqués", tone: "text-mz-status-bloque" },
      { key: "signes", label: "Signés", tone: "text-mz-success" },
      { key: "operationnels", label: "Opérationnels", tone: "text-mz-status-operationnel" },
      { key: "refuses", label: "Refusés", tone: "text-mz-text-disabled" },
    ],
  },
  {
    title: "Points à traiter",
    cards: [
      { key: "a_relancer", label: "À relancer", tone: "text-mz-warning" },
      { key: "contrats_a_signer", label: "Contrats à signer", tone: "text-mz-info" },
      { key: "aps_en_attente", label: "APS en attente", tone: "text-mz-warning" },
      { key: "doc_b_manquants", label: "Doc B manquants", tone: "text-mz-danger" },
      { key: "dossiers_incomplets", label: "Dossiers incomplets", tone: "text-mz-danger" },
    ],
  },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

useEffect(() => {
    api
      .get<DashboardStats>("/dashboard/stats")
      .then(({ data }) => setStats(data))
      .catch(() =>
        setError("Impossible de charger les statistiques. Le backend est-il démarré ?")
      );
  }, []);

if (error) return <p className="text-sm text-mz-danger">{error}</p>;
  if (!stats) return <p className="text-sm text-mz-text-muted">Chargement...</p>;

return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header className="border-b border-mz-border pb-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-mz-primary">
          MZ Building · Pilotage
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-mz-text">Vue d’ensemble</h2>
        <p className="mt-2 text-sm text-mz-text-muted">
          Suivi du portefeuille de sites et des actions à traiter.
        </p>
      </header>

{GROUPS.map((group) => (
        <section key={group.title} className="space-y-4">
          <h3 className="text-base font-semibold text-mz-text">{group.title}</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {group.cards.map(({ key, label, tone }) => {
              const metric = stats[key];

return (
                <Card
                  key={key}
                  className="transition duration-150 hover:-translate-y-0.5 hover:shadow-mz-2"
                >
                  <p className="text-sm font-medium text-mz-text-muted">{label}</p>
                  {metric.available ? (
                    <p className={`mt-4 text-3xl font-semibold ${tone}`}>
                      {metric.value.toLocaleString("fr-FR")}
                    </p>
                  ) : (
                    <div className="mt-4">
                      <p className="text-lg font-medium text-mz-text-disabled">À venir</p>
                      {metric.note && (
                        <p className="mt-1 text-xs text-mz-text-disabled">{metric.note}</p>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
