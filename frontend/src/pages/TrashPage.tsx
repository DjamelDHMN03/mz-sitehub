import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { RotateCcw, Trash2 } from "lucide-react";

interface SiteTrash {
  id: string;
  code: string;
  name: string | null;
  deleted_at: string;
}

export default function TrashPage() {
  const [sites, setSites] = useState<SiteTrash[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .get<SiteTrash[]>("/sites/trash")
      .then(({ data }) => setSites(data))
      .catch(() => setError("Impossible de charger la corbeille."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const restore = async (id: string, code: string) => {
    if (!confirm(`Restaurer le site ${code} ?`)) return;
    setRestoring(id);
    try {
      await api.post(`/sites/${id}/restore`);
      load();
    } catch {
      alert("Erreur lors de la restauration.");
    } finally {
      setRestoring(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-mz-text">Corbeille</h1>
          <p className="text-sm text-mz-text-muted mt-1">
            Sites supprimés — restaurez-les ou supprimez-les définitivement (ADMIN uniquement).
          </p>
        </div>
        <Button size="sm" variant="secondary" onClick={load}>Actualiser</Button>
      </div>

      {error && <p className="text-sm text-mz-danger">{error}</p>}
      {loading && <p className="text-sm text-mz-text-muted">Chargement...</p>}

      {!loading && sites.length === 0 && (
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-8 text-center">
          <Trash2 size={40} className="mx-auto mb-3 text-mz-text-disabled" />
          <p className="text-mz-text-muted">La corbeille est vide.</p>
        </div>
      )}

      {sites.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th>Code</Th>
              <Th>Nom</Th>
              <Th>Supprimé le</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <tbody>
            {sites.map((site) => (
              <Tr key={site.id}>
                <Td className="font-medium">{site.code}</Td>
                <Td>{site.name ?? "—"}</Td>
                <Td className="text-mz-text-muted text-xs">
                  {new Date(site.deleted_at).toLocaleDateString("fr-FR")}
                </Td>
                <Td>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => restore(site.id, site.code)}
                    disabled={restoring === site.id}
                  >
                    <RotateCcw size={13} />
                    {restoring === site.id ? "..." : "Restaurer"}
                  </Button>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
