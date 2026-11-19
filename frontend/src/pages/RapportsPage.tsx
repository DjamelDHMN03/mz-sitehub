import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Download, FileText, Package } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface SiteStatusOut {
  id: number;
  label: string;
}

async function downloadFile(url: string, filename: string) {
  const response = await api.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(blobUrl);
}

export default function RapportsPage() {
  const [statuses, setStatuses] = useState<SiteStatusOut[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [organisme, setOrganisme] = useState("");
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState("");

  useEffect(() => {
    api.get<SiteStatusOut[]>("/site-statuses").then(({ data }) => setStatuses(data));
    api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }).then(({ data }) => setSites(data));
  }, []);

  async function handleExportList(format: "xlsx" | "csv") {
    const params: Record<string, string> = { format };
    if (statusFilter) params.status_id = statusFilter;
    if (organisme) params.organisme = organisme;
    const query = new URLSearchParams(params).toString();
    await downloadFile(`/reports/sites/export?${query}`, `rapport_sites.${format}`);
  }

  async function handleFichePdf() {
    if (!selectedSiteId) return;
    const site = sites?.items.find((s) => s.id === selectedSiteId);
    await downloadFile(`/reports/sites/${selectedSiteId}/fiche-pdf`, `fiche_${site?.code ?? "site"}.pdf`);
  }

  async function handleExportComplet() {
    if (!selectedSiteId) return;
    const site = sites?.items.find((s) => s.id === selectedSiteId);
    await downloadFile(`/reports/sites/${selectedSiteId}/export-complet`, `${site?.code ?? "site"}_COMPLETE.zip`);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Rapport Sites (liste filtrée)</CardTitle></CardHeader>
        <div className="mb-3 flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm"
          >
            <option value="">Tous les statuts</option>
            {statuses.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <input
            placeholder="Filtrer par organisme"
            value={organisme}
            onChange={(e) => setOrganisme(e.target.value)}
            className="rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => handleExportList("xlsx")}><Download size={14} /> Excel</Button>
          <Button size="sm" variant="secondary" onClick={() => handleExportList("csv")}><Download size={14} /> CSV</Button>
        </div>
      </Card>

      <Card>
        <CardHeader><CardTitle>Fiche site / Export complet</CardTitle></CardHeader>
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="mb-3 w-full max-w-md rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm"
        >
          <option value="">— Choisir un site —</option>
          {sites?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.code} {s.name ? `— ${s.name}` : ""}</option>
          ))}
        </select>
        <div className="flex gap-2">
          <Button size="sm" disabled={!selectedSiteId} onClick={handleFichePdf}>
            <FileText size={14} /> Fiche PDF
          </Button>
          <Button size="sm" variant="secondary" disabled={!selectedSiteId} onClick={handleExportComplet}>
            <Package size={14} /> Export complet (ZIP)
          </Button>
        </div>
      </Card>
    </div>
  );
}
