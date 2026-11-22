import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { api } from "@/lib/api";
import { MapPopup } from "@/components/MapPopup";
import SiteFormModal from "@/components/SiteFormModal";
import type { SiteListResponse } from "@/lib/types";

type SiteItem = SiteListResponse["items"][number];

interface SiteStatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
}

// Centre par defaut : Algerie
const ALGERIA_CENTER: [number, number] = [28.0339, 1.6596];
const ALGERIA_DEFAULT_ZOOM = 5;
const PAGE_SIZE = 200; // maximum accepte par l'API
const MAX_PAGES = 50; // garde-fou

/** Icone de marker coloree dynamiquement (pas d'image externe) */
function makeColoredIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width: 16px; height: 16px; border-radius: 50%;
      background: ${color}; border: 2px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,0.5);
    "></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  });
}

/** Charge TOUTES les pages de sites (API limitee a 200 par page). */
async function fetchAllSites(): Promise<SiteItem[]> {
  const byId = new Map<string, SiteItem>();
  for (let page = 1; page <= MAX_PAGES; page++) {
    const { data } = await api.get<SiteListResponse>("/sites", {
      params: { page, page_size: PAGE_SIZE },
    });
    data.items.forEach((s) => byId.set(s.id, s));
    if (data.items.length === 0 || byId.size >= data.total) break;
  }
  return Array.from(byId.values());
}

export default function CartePage() {
  const [searchParams] = useSearchParams();
  const [sites, setSites] = useState<SiteItem[] | null>(null);
  const [statuses, setStatuses] = useState<Record<number, SiteStatusOut>>({});
  const [statusFilter, setStatusFilter] = useState<number | "all">("all");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [editId, setEditId] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<SiteStatusOut[]>("/site-statuses")
      .then(({ data }) => {
        setStatuses(Object.fromEntries(data.map((s) => [s.id, s])));
        const statusCode = searchParams.get("status");
        if (statusCode) {
          const match = data.find((s) => s.code === statusCode);
          if (match) setStatusFilter(match.id);
        }
      })
      .catch(() => {
        /* non bloquant */
      });
  }, [searchParams]);

  useEffect(() => {
    setError(null);
    fetchAllSites()
      .then(setSites)
      .catch(() => setError("Impossible de charger les sites."));
  }, [reloadKey]);

  const withGps = useMemo(
    () => (sites ?? []).filter((s) => s.latitude !== null && s.longitude !== null),
    [sites]
  );

  const shown = useMemo(
    () => withGps.filter((s) => statusFilter === "all" || s.status_id === statusFilter),
    [withGps, statusFilter]
  );

  const missingGps = sites ? sites.length - withGps.length : 0;

  const legendEntries = useMemo(() => {
    const seen = new Map<string, string>();
    Object.values(statuses).forEach((s) => {
      if (!seen.has(s.color)) seen.set(s.color, s.label);
    });
    return Array.from(seen.entries());
  }, [statuses]);

  const statusOptions = useMemo(
    () =>
      Object.values(statuses)
        .sort((a, b) => a.id - b.id)
        .map((s) => ({ id: s.id, label: s.label })),
    [statuses]
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <div className="isolate flex-1 overflow-hidden rounded-mz-lg border border-mz-border">
        {error && <p className="p-4 text-sm text-mz-danger">{error}</p>}

        <MapContainer
          center={ALGERIA_CENTER}
          zoom={ALGERIA_DEFAULT_ZOOM}
          className="h-full w-full"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MarkerClusterGroup chunkedLoading>
            {shown.map((site) => {
              const status = statuses[site.status_id];
              const color = status?.color ?? "#6E687A";
              return (
                <Marker
                  key={site.id}
                  position={[site.latitude as number, site.longitude as number]}
                  icon={makeColoredIcon(color)}
                >
                  <Popup>
                    <MapPopup
                      siteId={site.id}
                      code={site.code}
                      name={site.name}
                      statusLabel={status?.label ?? `#${site.status_id}`}
                      statusColor={color}
                      latitude={site.latitude as number}
                      longitude={site.longitude as number}
                      onEdit={setEditId}
                    />
                  </Popup>
                </Marker>
              );
            })}
          </MarkerClusterGroup>
        </MapContainer>
      </div>

      <aside className="w-64 shrink-0 space-y-4 overflow-y-auto">
        <div className="rounded-mz-lg border border-mz-border bg-mz-card p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mz-text-muted">
            Filtrer par statut
          </p>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="w-full rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm text-mz-text"
          >
            <option value="all">Tous les statuts</option>
            {statusOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-mz-lg border border-mz-border bg-mz-card p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mz-text-muted">
            {"L\u00e9gende"}
          </p>
          <ul className="space-y-1.5">
            {legendEntries.map(([color, label]) => (
              <li key={color} className="flex items-center gap-2 text-sm text-mz-text">
                <span className="h-2.5 w-2.5 rounded-full border border-white/40" style={{ background: color }} />
                {label}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-mz-text-disabled">
          {sites === null
            ? "Chargement des sites..."
            : `${shown.length} site(s) affich\u00e9(s) sur ${sites.length}.`}
        </p>
        {missingGps > 0 && (
          <p className="text-xs text-mz-warning">
            {missingGps} {"site(s) sans coordonn\u00e9es GPS, impossibles \u00e0 placer sur la carte."}{" "}
            <Link to="/sites" className="underline">
              Voir la liste
            </Link>
          </p>
        )}
      </aside>

      {editId && (
        <SiteFormModal
          siteId={editId}
          statuses={statusOptions}
          onClose={() => setEditId(null)}
          onSaved={() => {
            setEditId(null);
            setReloadKey((k) => k + 1);
            window.dispatchEvent(new Event("mz:sites-changed"));
          }}
        />
      )}
    </div>
  );
}