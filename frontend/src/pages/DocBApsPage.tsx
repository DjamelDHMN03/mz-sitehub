import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Plus } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface DocumentOut {
  id: string;
  filename: string;
}

interface DocBOut {
  id: string;
  date_preparation: string | null;
  date_depot: string | null;
  organisme: string | null;
  reference: string | null;
  status: string | null;
  document_id: string | null;
  version: number | null;
  observation: string | null;
}

interface ApsOut {
  id: string;
  aps_type: string | null;
  version: number | null;
  document_id: string | null;
  observation: string | null;
}

const APS_TYPES = [
  "APS_V1", "APS_V2", "APS_V3", "PLAN_GC", "PLAN_STRUCTURE",
  "PLAN_TOITURE", "PLAN_PYLONE", "PLAN_RADIO", "TSS", "PHOTO_TECHNIQUE",
];

export default function DocBApsPage() {
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [docBList, setDocBList] = useState<DocBOut[]>([]);
  const [apsList, setApsList] = useState<ApsOut[]>([]);
  const [showNewDocB, setShowNewDocB] = useState(false);
  const [showNewAps, setShowNewAps] = useState(false);

  useEffect(() => {
    api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }).then(({ data }) => setSites(data));
  }, []);

  useEffect(() => {
    if (!selectedSiteId) return;
    refreshAll();
  }, [selectedSiteId]);

  async function refreshAll() {
    const [docs, docB, aps] = await Promise.all([
      api.get<DocumentOut[]>(`/sites/${selectedSiteId}/documents`),
      api.get<DocBOut[]>(`/sites/${selectedSiteId}/doc-b`),
      api.get<ApsOut[]>(`/sites/${selectedSiteId}/aps`),
    ]);
    setDocuments(docs.data);
    setDocBList(docB.data);
    setApsList(aps.data);
  }

  async function handleCreateDocB(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(
      Array.from(form.entries()).filter(([, v]) => v !== "")
    );
    await api.post(`/sites/${selectedSiteId}/doc-b`, payload);
    await refreshAll();
    setShowNewDocB(false);
  }

  async function handleCreateAps(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(
      Array.from(form.entries()).filter(([, v]) => v !== "")
    );
    await api.post(`/sites/${selectedSiteId}/aps`, payload);
    await refreshAll();
    setShowNewAps(false);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Site</CardTitle></CardHeader>
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="w-full max-w-md rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm text-mz-text"
        >
          <option value="">— Choisir un site —</option>
          {sites?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.code} {s.name ? `— ${s.name}` : ""}</option>
          ))}
        </select>
      </Card>

      {selectedSiteId && (
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Doc B</CardTitle>
              <Button size="sm" variant="ghost" onClick={() => setShowNewDocB(!showNewDocB)}><Plus size={14} /></Button>
            </CardHeader>

            {showNewDocB && (
              <form onSubmit={handleCreateDocB} className="mb-3 space-y-1.5 rounded-mz-md border border-mz-border p-3">
                <input name="reference" placeholder="Référence" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                <input name="organisme" placeholder="Organisme" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                <div className="flex gap-1.5">
                  <input name="date_preparation" type="date" title="Date préparation" className="w-1/2 rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                  <input name="date_depot" type="date" title="Date dépôt" className="w-1/2 rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                </div>
                <input name="status" placeholder="Statut" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                <select name="document_id" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                  <option value="">Lier un document (optionnel)...</option>
                  {documents.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
                </select>
                <textarea name="observation" placeholder="Observation" rows={2} className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                <Button type="submit" size="sm">Enregistrer</Button>
              </form>
            )}

            <ul className="space-y-2">
              {docBList.map((d) => (
                <li key={d.id} className="rounded-mz-md border border-mz-border p-2.5 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-mz-text">{d.reference ?? "Sans référence"}</span>
                    {d.status && <Badge tone="info">{d.status}</Badge>}
                  </div>
                  <p className="text-xs text-mz-text-muted">
                    {d.organisme ?? "À COMPLÉTER"} · déposé le {d.date_depot ?? "—"}
                  </p>
                </li>
              ))}
              {docBList.length === 0 && <p className="text-sm text-mz-text-muted">Aucun Doc B pour ce site.</p>}
            </ul>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>APS / Plans</CardTitle>
              <Button size="sm" variant="ghost" onClick={() => setShowNewAps(!showNewAps)}><Plus size={14} /></Button>
            </CardHeader>

            {showNewAps && (
              <form onSubmit={handleCreateAps} className="mb-3 space-y-1.5 rounded-mz-md border border-mz-border p-3">
                <select name="aps_type" required className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                  <option value="">Type...</option>
                  {APS_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <select name="document_id" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                  <option value="">Lier un document (optionnel)...</option>
                  {documents.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
                </select>
                <textarea name="observation" placeholder="Observation" rows={2} className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                <Button type="submit" size="sm">Enregistrer</Button>
              </form>
            )}

            <ul className="space-y-2">
              {apsList.map((a) => (
                <li key={a.id} className="rounded-mz-md border border-mz-border p-2.5 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-mz-text">{a.aps_type}</span>
                    <Badge>V{a.version ?? 1}</Badge>
                  </div>
                  {a.observation && <p className="text-xs text-mz-text-muted">{a.observation}</p>}
                </li>
              ))}
              {apsList.length === 0 && <p className="text-sm text-mz-text-muted">Aucun APS pour ce site.</p>}
            </ul>
          </Card>
        </div>
      )}
    </div>
  );
}
