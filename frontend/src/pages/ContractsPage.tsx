import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Plus, FileSignature } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface ContractOut {
  id: string;
  reference: string | null;
  contract_type: string | null;
  status: string | null;
  amount: number | null;
  date_start: string | null;
  date_end: string | null;
  date_signed: string | null;
  date_expiration: string | null;
  observation: string | null;
}

interface SignatoryOut {
  id: string;
  party: "PROPRIETAIRE" | "OOREDOO";
  name: string | null;
  role_label: string | null;
  has_signing_power: boolean | null;
}

function formatAmount(amount: number | null): string {
  if (amount === null) return "À COMPLÉTER";
  return new Intl.NumberFormat("fr-DZ").format(amount) + " DA";
}

export default function ContractsPage() {
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [contracts, setContracts] = useState<ContractOut[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);
  const [signatories, setSignatories] = useState<SignatoryOut[]>([]);
  const [showNewContract, setShowNewContract] = useState(false);
  const [showNewSignatory, setShowNewSignatory] = useState(false);

  useEffect(() => {
    api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }).then(({ data }) => setSites(data));
  }, []);

  useEffect(() => {
    if (!selectedSiteId) return;
    refreshContracts();
  }, [selectedSiteId]);

  useEffect(() => {
    if (!selectedContractId) {
      setSignatories([]);
      return;
    }
    api.get<SignatoryOut[]>(`/contracts/${selectedContractId}/signatories`).then(({ data }) => setSignatories(data));
  }, [selectedContractId]);

  async function refreshContracts() {
    const { data } = await api.get<ContractOut[]>(`/sites/${selectedSiteId}/contracts`);
    setContracts(data);
  }

  async function handleCreateContract(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(
      Array.from(form.entries()).filter(([, v]) => v !== "")
    );
    await api.post(`/sites/${selectedSiteId}/contracts`, payload);
    await refreshContracts();
    setShowNewContract(false);
  }

  async function handleAddSignatory(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedContractId) return;
    const form = new FormData(e.currentTarget);
    const payload: Record<string, unknown> = Object.fromEntries(form.entries());
    payload.has_signing_power = form.get("has_signing_power") === "on";
    await api.post(`/contracts/${selectedContractId}/signatories`, payload);
    const { data } = await api.get<SignatoryOut[]>(`/contracts/${selectedContractId}/signatories`);
    setSignatories(data);
    setShowNewSignatory(false);
  }

  const selectedContract = contracts.find((c) => c.id === selectedContractId) ?? null;

  return (
    <div className="grid grid-cols-3 gap-4">
      <Card className="col-span-1">
        <CardHeader><CardTitle>Site</CardTitle></CardHeader>
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="w-full rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm text-mz-text"
        >
          <option value="">— Choisir un site —</option>
          {sites?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.code} {s.name ? `— ${s.name}` : ""}</option>
          ))}
        </select>

        {selectedSiteId && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-mz-text-muted">Contrats</p>
              <Button size="sm" variant="ghost" onClick={() => setShowNewContract(!showNewContract)}><Plus size={14} /></Button>
            </div>

            {showNewContract && (
              <form onSubmit={handleCreateContract} className="space-y-1.5 rounded-mz-md border border-mz-border p-2">
                <input name="reference" placeholder="Référence" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="contract_type" placeholder="Type de contrat" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="status" placeholder="Statut" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="amount" type="number" step="0.01" placeholder="Montant (DA) — laisser vide si inconnu" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="duration_years" type="number" step="0.5" placeholder="Durée (années)" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <Button type="submit" size="sm" className="w-full text-xs">Ajouter</Button>
              </form>
            )}

            <ul className="space-y-1">
              {contracts.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => setSelectedContractId(c.id)}
                    className={`w-full rounded-mz-md px-2 py-1.5 text-left text-sm transition-colors ${
                      selectedContractId === c.id ? "bg-mz-primary/15 text-mz-primary" : "hover:bg-mz-surface-2 text-mz-text"
                    }`}
                  >
                    <p className="font-medium">{c.reference ?? "Sans référence"}</p>
                    {c.status && <p className="text-xs text-mz-text-muted">{c.status}</p>}
                  </button>
                </li>
              ))}
              {contracts.length === 0 && <p className="text-xs text-mz-text-muted">Aucun contrat pour ce site.</p>}
            </ul>
          </div>
        )}
      </Card>

      <Card className="col-span-2">
        {!selectedContract ? (
          <p className="text-sm text-mz-text-muted">Sélectionnez un contrat pour voir son détail.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <CardHeader><CardTitle>{selectedContract.reference ?? "Sans référence"}</CardTitle></CardHeader>
              <div className="flex flex-wrap gap-2">
                {selectedContract.status && <Badge tone="info">{selectedContract.status}</Badge>}
                {selectedContract.contract_type && <Badge>{selectedContract.contract_type}</Badge>}
              </div>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-mz-text-muted">
                <p>💰 {formatAmount(selectedContract.amount)}</p>
                <p>📅 Début : {selectedContract.date_start ?? "À COMPLÉTER"}</p>
                <p>📅 Fin : {selectedContract.date_end ?? "À COMPLÉTER"}</p>
                <p>⏰ Expiration : {selectedContract.date_expiration ?? "À COMPLÉTER"}</p>
              </div>
              {selectedContract.observation && (
                <p className="mt-2 text-sm text-mz-text">{selectedContract.observation}</p>
              )}
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-mz-text-muted">Signataires</p>
                <Button size="sm" variant="secondary" onClick={() => setShowNewSignatory(!showNewSignatory)}>
                  <Plus size={13} /> Ajouter un signataire
                </Button>
              </div>

              {showNewSignatory && (
                <form onSubmit={handleAddSignatory} className="mb-3 space-y-1.5 rounded-mz-md border border-mz-border p-3">
                  <select name="party" required className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                    <option value="PROPRIETAIRE">Propriétaire</option>
                    <option value="OOREDOO">Ooredoo</option>
                  </select>
                  <input name="name" placeholder="Nom" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                  <input name="role_label" placeholder="Fonction" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                  <label className="flex items-center gap-2 text-xs text-mz-text-muted">
                    <input type="checkbox" name="has_signing_power" />
                    Pouvoir de signature vérifié
                  </label>
                  <Button type="submit" size="sm">Enregistrer</Button>
                </form>
              )}

              <ul className="space-y-2">
                {signatories.map((s) => (
                  <li key={s.id} className="flex items-center justify-between rounded-mz-md border border-mz-border p-2.5">
                    <div className="flex items-center gap-2">
                      <FileSignature size={14} className="text-mz-text-muted" />
                      <div>
                        <p className="text-sm text-mz-text">{s.name ?? "À COMPLÉTER"}</p>
                        <p className="text-xs text-mz-text-muted">{s.role_label ?? "—"}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={s.party === "OOREDOO" ? "danger" : "neutral"}>{s.party}</Badge>
                      {s.has_signing_power === null && <Badge tone="warning">Pouvoir à vérifier</Badge>}
                      {s.has_signing_power === true && <Badge tone="success">Pouvoir vérifié</Badge>}
                    </div>
                  </li>
                ))}
                {signatories.length === 0 && <p className="text-sm text-mz-text-muted">Aucun signataire enregistré.</p>}
              </ul>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
