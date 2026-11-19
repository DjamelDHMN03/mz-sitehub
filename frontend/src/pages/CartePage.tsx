import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { api } from "@/lib/api";
import { MapPopup } from "@/components/MapPopup";
import type { SiteListResponse } from "@/lib/types";

interface SiteStatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
}

// Centre par défaut : Algérie (section 20 — carte interactive de l'Algérie)
const ALGERIA_CENTER: [number, number] = [28.0339, 1.6596];
const ALGERIA_DEFAULT_ZOOM = 5;

/** Icône de marker colorée dynamiquement (pas d'image externe, section 21) */
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

export default function CartePage() {
  const [searchParams] = useSearchParams();
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [statuses, setStatuses] = useState<Record<number, SiteStatusOut>>({});
  const [statusFilter, setStatusFilter] = useState<number | "all">("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<SiteStatusOut[]>("/site-statuses").then(({ data }) => {
      const byId = Object.fromEntries(data.map((s) => [s.id, s]));
      setStatuses(byId);

      // Applique le filtre reçu depuis l'Assistant IA (section 63), une fois
      // les statuts chargés (on a besoin du code -> id).
      const statusCode = searchParams.get("status");
      if (statusCode) {
        const match = data.find((s) => s.code === statusCode);
        if (match) setStatusFilter(match.id);
      }
    });
  }, [searchParams]);

  useEffect(() => {
    api
      .get<SiteListResponse>("/sites", { params: { page_size: 200 } })
      .then(({ data }) => setSites(data))
      .catch(() => setError("Impossible de charger les sites."));
  }, []);

  const sitesWithGps = useMemo(() => {
    if (!sites) return [];
    return sites.items.filter(
      (s) =>
        s.latitude !== null &&
        s.longitude !== null &&
        (statusFilter === "all" || s.status_id === statusFilter)
    );
  }, [sites, statusFilter]);

  // Légende : couleurs distinctes réellement utilisées par les statuts (section 21)
  const legendEntries = useMemo(() => {
    const seen = new Map<string, string>(); // color -> label représentatif
    Object.values(statuses).forEach((s) => {
      if (!seen.has(s.color)) seen.set(s.color, s.label);
    });
    return Array.from(seen.entries());
  }, [statuses]);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <div className="flex-1 overflow-hidden rounded-mz-lg border border-mz-border">
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
            {sitesWithGps.map((site) => {
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
                      code={site.code}
                      name={site.name}
                      statusLabel={status?.label ?? `#${site.status_id}`}
                      statusColor={color}
                      latitude={site.latitude as number}
                      longitude={site.longitude as number}
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
            {Object.values(statuses).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-mz-lg border border-mz-border bg-mz-card p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mz-text-muted">
            Légende
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
          {sitesWithGps.length} site(s) affiché(s) avec coordonnées GPS
          {sites && sites.total > sitesWithGps.length
            ? ` — ${sites.total - sitesWithGps.length} sans GPS non affiché(s)`
            : ""}
          .
        </p>
      </aside>
    </div>
  );
}
