import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";

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

const CARDS: { key: keyof DashboardStats; label: string; tone: string }[] = [
  { key: "total_sites", label: "Total sites", tone: "text-mz-text" },
  { key: "nouveaux", label: "Nouveaux", tone: "text-mz-status-nouveau" },
  { key: "en_cours", label: "En cours", tone: "text-mz-status-en-cours" },
  { key: "negociation", label: "Négociation", tone: "text-mz-status-attente" },
  { key: "bloques", label: "Bloqués", tone: "text-mz-status-bloque" },
  { key: "signes", label: "Signés", tone: "text-mz-success" },
  { key: "operationnels", label: "Opérationnels", tone: "text-mz-status-operationnel" },
  { key: "refuses", label: "Refusés", tone: "text-mz-text-disabled" },
  { key: "a_relancer", label: "À relancer", tone: "text-mz-warning" },
  { key: "contrats_a_signer", label: "Contrats à signer", tone: "text-mz-info" },
  { key: "aps_en_attente", label: "APS en attente", tone: "text-mz-warning" },
  { key: "doc_b_manquants", label: "Doc B manquants", tone: "text-mz-danger" },
  { key: "dossiers_incomplets", label: "Dossiers incomplets", tone: "text-mz-danger" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardStats>("/dashboard/stats")
      .then(({ data }) => setStats(data))
      .catch(() => setError("Impossible de charger les statistiques. Le backend est-il démarré ?"));
  }, []);

  if (error) return <p className="text-sm text-mz-danger">{error}</p>;
  if (!stats) return <p className="text-sm text-mz-text-muted">Chargement...</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {CARDS.map(({ key, label, tone }) => {
          const metric = stats[key];
          return (
            <Card key={key}>
              <CardHeader>
                <CardTitle>{label}</CardTitle>
              </CardHeader>
              {metric.available ? (
                <p className={`text-3xl font-semibold ${tone}`}>{metric.value}</p>
              ) : (
                <div>
                  <p className="text-lg font-medium text-mz-text-disabled">à venir</p>
                  {metric.note && <p className="mt-1 text-xs text-mz-text-disabled">{metric.note}</p>}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
