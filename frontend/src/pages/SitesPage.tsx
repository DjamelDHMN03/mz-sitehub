import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Star, Kanban, FileSpreadsheet } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface SiteStatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
}

export default function SitesPage() {
  const [data, setData] = useState<SiteListResponse | null>(null);
  const [statuses, setStatuses] = useState<Record<number, SiteStatusOut>>({});
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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
  }, [search]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          placeholder="Rechercher un code, un nom, un propriétaire..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-80 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary"
        />
        {data && (
          <p className="text-sm text-mz-text-muted">{data.total} site(s)</p>
        )}
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
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}
