import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import type { SiteListResponse, SiteListItem } from "@/lib/types";

interface SiteStatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
  sort_order: number;
}

export default function KanbanPage() {
  const [sites, setSites] = useState<SiteListItem[]>([]);
  const [statuses, setStatuses] = useState<SiteStatusOut[]>([]);

  async function refresh() {
    const [sitesRes, statusesRes] = await Promise.all([
      api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }),
      api.get<SiteStatusOut[]>("/site-statuses"),
    ]);
    setSites(sitesRes.data.items);
    setStatuses(statusesRes.data.sort((a, b) => a.sort_order - b.sort_order));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function moveSite(siteId: string, newStatusId: number) {
    await api.patch(`/sites/${siteId}`, { status_id: newStatusId });
    await refresh();
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {statuses.map((status) => {
        const columnSites = sites.filter((s) => s.status_id === status.id);
        return (
          <div key={status.id} className="w-64 shrink-0">
            <div
              className="mb-2 flex items-center justify-between rounded-mz-md px-3 py-1.5 text-sm font-medium"
              style={{ backgroundColor: `${status.color}26`, color: status.color }}
            >
              <span>{status.label}</span>
              <span>{columnSites.length}</span>
            </div>

            <div className="space-y-2">
              {columnSites.map((site) => (
                <Card key={site.id} className="p-3">
                  <p className="text-sm font-medium text-mz-text">{site.code}</p>
                  {site.name && <p className="text-xs text-mz-text-muted">{site.name}</p>}
                  <select
                    value={status.id}
                    onChange={(e) => moveSite(site.id, Number(e.target.value))}
                    className="mt-2 w-full rounded-mz-sm border border-mz-border bg-mz-input px-1.5 py-1 text-xs"
                  >
                    {statuses.map((s) => (
                      <option key={s.id} value={s.id}>{s.label}</option>
                    ))}
                  </select>
                </Card>
              ))}
              {columnSites.length === 0 && (
                <p className="text-xs text-mz-text-disabled">Aucun site</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
