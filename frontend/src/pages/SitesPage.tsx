import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import SiteFormModal from "@/components/SiteFormModal";
import { Star, Kanban, FileSpreadsheet, Plus, Pencil, Trash2 } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface SiteStatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
}

type FormTarget = { mode: "create" } | { mode: "edit"; id: string };

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return "La suppression a échoué. Réessayez.";
}

export default function SitesPage() {
  const [data, setData] = useState<SiteListResponse | null>(null);
  const [statuses, setStatuses] = useState<Record<number, SiteStatusOut>>({});
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [formTarget, setFormTarget] = useState<FormTarget | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; code: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<SiteStatusOut[]>("/site-statuses")
      .then(({ data }) => setStatuses(Object.fromEntries(data.map((s) => [s.id, s]))))
      .catch(() => {
        /* si ça échoue, les badges retombent sur l'id brut — pas bloquant */
      });
  }, []);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    const timeout = setTimeout(() => {
      api
        .get<SiteListResponse>("/sites", { params: { q: search || undefined, page_size: 50 } })
        .then(({ data }) => setData(data))
        .catch(() => setError("Impossible de charger les sites. Le backend est-il démarré ?"))
        .finally(() => setIsLoading(false));
    }, 300); // debounce recherche

    return () => clearTimeout(timeout);
  }, [search, reloadKey]);

  const statusOptions = Object.values(statuses)
    .sort((a, b) => a.id - b.id)
    .map((s) => ({ id: s.id, label: s.label }));

  function handleSaved() {
    setFormTarget(null);
    setReloadKey((k) => k + 1);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.delete(`/sites/${deleteTarget.id}`);
      setDeleteTarget(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setDeleteError(errorMessage(err));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <input
          type="text"
          placeholder="Rechercher un code, un nom, un propriétaire..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-80 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary"
        />
        {data && <p className="text-sm text-mz-text-muted">{data.total} site(s)</p>}
        <Button size="sm" onClick={() => setFormTarget({ mode: "create" })}>
          <Plus size={14} /> Ajouter un site
        </Button>
        <Link to="/kanban">
          <Button size="sm" variant="secondary"><Kanban size={14} /> Vue Kanban</Button>
        </Link>
        <Link to="/sites/importer-excel">
          <Button size="sm" variant="secondary"><FileSpreadsheet size={14} /> Importer Excel</Button>
        </Link>
      </div>

      {error && <p className="text-sm text-mz-danger">{error}</p>}
      {isLoading && !data && <p className="text-sm text-mz-text-muted">Chargement...</p>}

      {data && data.items.length === 0 && !isLoading && (
        <p className="text-sm text-mz-text-muted">Aucun site ne correspond à cette recherche.</p>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th></Th>
              <Th>Code</Th>
              <Th>Nom</Th>
              <Th>Statut</Th>
              <Th>Priorité</Th>
              <Th>GPS</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <tbody>
            {data.items.map((site) => {
              const status = statuses[site.status_id];
              return (
                <Tr key={site.id}>
                  <Td>
                    {site.is_favorite && <Star size={14} className="fill-mz-warning text-mz-warning" />}
                  </Td>
                  <Td className="font-medium">
                    <Link to={`/sites/${site.id}`} className="text-mz-primary hover:underline">
                      {site.code}
                    </Link>
                  </Td>
                  <Td>{site.name ?? "—"}</Td>
                  <Td>
                    {status ? (
                      <StatusBadge label={status.label} color={status.color} />
                    ) : (
                      <span className="text-mz-text-disabled text-xs">#{site.status_id}</span>
                    )}
                  </Td>
                  <Td>{site.priority}</Td>
                  <Td className="text-mz-text-muted text-xs">
                    {site.latitude && site.longitude
                      ? `${site.latitude.toFixed(4)}, ${site.longitude.toFixed(4)}`
                      : "À COMPLÉTER"}
                  </Td>
                  <Td>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setFormTarget({ mode: "edit", id: site.id })}
                        aria-label={`Modifier le site ${site.code}`}
                        title="Modifier"
                        className="rounded-mz-md p-1.5 text-mz-text-muted hover:text-mz-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteError(null);
                          setDeleteTarget({ id: site.id, code: site.code });
                        }}
                        aria-label={`Supprimer le site ${site.code}`}
                        title="Supprimer"
                        className="rounded-mz-md p-1.5 text-mz-text-muted hover:text-mz-danger focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}

      {formTarget && (
        <SiteFormModal
          siteId={formTarget.mode === "edit" ? formTarget.id : null}
          statuses={statusOptions}
          onClose={() => setFormTarget(null)}
          onSaved={handleSaved}
        />
      )}

      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="alertdialog"
          aria-modal="true"
          aria-label="Confirmer la suppression"
        >
          <Card className="w-full max-w-sm">
            <h2 className="mb-2 text-base font-semibold text-mz-text">Supprimer ce site ?</h2>
            <p className="mb-4 text-sm text-mz-text-muted">
              Le site <span className="font-medium text-mz-text">{deleteTarget.code}</span> sera déplacé
              dans la corbeille. Vous pourrez le restaurer ensuite.
            </p>
            {deleteError && <p className="mb-3 text-sm text-mz-danger">{deleteError}</p>}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
              >
                Annuler
              </Button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={isDeleting}
                className="rounded-mz-md bg-mz-danger px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-danger disabled:opacity-60"
              >
                {isDeleting ? "Suppression..." : "Supprimer"}
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}