import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { Button } from "@/components/Button";
import { RefreshCw, TrendingUp, Users, AlertTriangle, CheckCircle, Clock } from "lucide-react";

// ------------------------------------------------------------------ types
interface KPIs {
  total_sites: number;
  sites_boucles: number;
  sites_en_cours: number;
  sites_bloques: number;
  sites_sans_categorie: number;
  delai_moyen_doc_b: number | null;
  loyer_moyen_da: number | null;
  sites_avec_loyer: number;
  sites_avec_gps: number;
}

interface WilayaStat {
  wilaya: string;
  total: number;
  boucles: number;
  en_cours: number;
  bloques: number;
}

interface NegociateurStat {
  negociateur: string;
  type_contrat: string | null;
  total_sites: number;
  boucles: number;
  en_cours: number;
  bloques: number;
  delai_moyen_doc_b: number | null;
  loyer_moyen_da: number | null;
}

interface SiteItem {
  id: string;
  code: string;
  owner_name: string | null;
  commune_name: string | null;
  wilaya_name: string | null;
  negociateur_nom: string | null;
  project: string | null;
  progress_category: "BOUCLE" | "EN_COURS" | "BLOQUE" | null;
  progress_stage: string | null;
  progress_raw: string | null;
  rent_negotiated: number | null;
  doc_b_date: string | null;
  doc_b_delay_days: number | null;
  tss_date: string | null;
  contract_date: string | null;
  site_typology: string | null;
  site_model: string | null;
}

// ------------------------------------------------------------------ helpers
const CATEGORY_CONFIG = {
  BOUCLE: { label: "Bouclé", bg: "bg-emerald-100 text-emerald-800", dot: "bg-emerald-500" },
  EN_COURS: { label: "En cours", bg: "bg-blue-100 text-blue-800", dot: "bg-blue-500" },
  BLOQUE: { label: "Bloqué", bg: "bg-red-100 text-red-800", dot: "bg-red-500" },
} as const;

function CategoryBadge({ cat }: { cat: string | null }) {
  if (!cat) return <span className="text-xs text-mz-text-disabled">—</span>;
  const cfg = CATEGORY_CONFIG[cat as keyof typeof CATEGORY_CONFIG];
  if (!cfg) return <span className="text-xs">{cat}</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function fmt(n: number | null | undefined, suffix = "") {
  if (n == null) return "—";
  return n.toLocaleString("fr-DZ") + suffix;
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-mz-border overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-mz-text-muted w-6">{value}</span>
    </div>
  );
}

// ------------------------------------------------------------------ page
export default function OorédooCentrePage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [wilayas, setWilayas] = useState<WilayaStat[]>([]);
  const [negociateurs, setNegociateurs] = useState<NegociateurStat[]>([]);
  const [sites, setSites] = useState<SiteItem[]>([]);
  const [sitesTotal, setSitesTotal] = useState(0);
  const [catFilter, setCatFilter] = useState<string>("");
  const [negFilter, setNegFilter] = useState("");
  const [wilayaFilter, setWilayaFilter] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"negociateurs" | "sites" | "wilayas">("negociateurs");

  const loadStats = useCallback(() => {
    api.get<{ kpis: KPIs; par_wilaya: WilayaStat[] }>("/ooredoo-centre/stats")
      .then(({ data }) => { setKpis(data.kpis); setWilayas(data.par_wilaya); })
      .catch(() => setError("Impossible de charger les statistiques."));
  }, []);

  const loadNegociateurs = useCallback(() => {
    api.get<NegociateurStat[]>("/ooredoo-centre/negociateurs")
      .then(({ data }) => setNegociateurs(data))
      .catch(() => {});
  }, []);

  const loadSites = useCallback(() => {
    const params: Record<string, string> = { page_size: "100" };
    if (catFilter) params.progress_category = catFilter;
    if (negFilter) params.negotiator = negFilter;
    if (wilayaFilter) params.wilaya = wilayaFilter;
    api.get<{ total: number; items: SiteItem[] }>("/ooredoo-centre/sites", { params })
      .then(({ data }) => { setSites(data.items); setSitesTotal(data.total); })
      .catch(() => {});
  }, [catFilter, negFilter, wilayaFilter]);

  useEffect(() => { loadStats(); loadNegociateurs(); }, [loadStats, loadNegociateurs]);
  useEffect(() => { loadSites(); }, [loadSites]);

  const handleSync = async () => {
    setSyncing(true); setSyncMsg(null);
    try {
      const { data } = await api.post<{ message: string }>("/ooredoo-centre/sync");
      setSyncMsg(data.message);
      setTimeout(() => { loadStats(); loadNegociateurs(); loadSites(); }, 35000);
    } catch {
      setSyncMsg("Erreur lors du déclenchement de la synchronisation.");
    } finally {
      setSyncing(false);
    }
  };

  if (error) return <p className="text-sm text-mz-danger">{error}</p>;

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-mz-text">Suivi Ooredoo Centre</h1>
          <p className="text-sm text-mz-text-muted">
            {kpis ? `${kpis.total_sites} sites · 12 négociateurs` : "Chargement…"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {syncMsg && <p className="text-xs text-mz-text-muted max-w-xs">{syncMsg}</p>}
          <Button size="sm" variant="secondary" onClick={handleSync} disabled={syncing}>
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Synchro…" : "Synchroniser"}
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      {kpis && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
          <Card>
            <CardHeader><CardTitle>Total sites</CardTitle></CardHeader>
            <p className="text-3xl font-bold text-mz-text">{kpis.total_sites}</p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1">
                <CheckCircle size={13} className="text-emerald-500" />Bouclés
              </CardTitle>
            </CardHeader>
            <p className="text-3xl font-bold text-emerald-600">{kpis.sites_boucles}</p>
            <p className="text-xs text-mz-text-muted">
              {kpis.total_sites > 0 ? Math.round((kpis.sites_boucles / kpis.total_sites) * 100) : 0}%
            </p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1">
                <Clock size={13} className="text-blue-500" />En cours
              </CardTitle>
            </CardHeader>
            <p className="text-3xl font-bold text-blue-600">{kpis.sites_en_cours}</p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1">
                <AlertTriangle size={13} className="text-red-500" />Bloqués
              </CardTitle>
            </CardHeader>
            <p className="text-3xl font-bold text-red-600">{kpis.sites_bloques}</p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1">
                <TrendingUp size={13} className="text-mz-primary" />Loyer moyen
              </CardTitle>
            </CardHeader>
            <p className="text-2xl font-bold text-mz-text">{fmt(kpis.loyer_moyen_da)}</p>
            <p className="text-xs text-mz-text-muted">DA/mois · {kpis.sites_avec_loyer} sites</p>
          </Card>
          <Card>
            <CardHeader><CardTitle>Délai moy. Doc B</CardTitle></CardHeader>
            <p className="text-2xl font-bold text-mz-text">{fmt(kpis.delai_moyen_doc_b)}</p>
            <p className="text-xs text-mz-text-muted">jours</p>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-mz-border">
        {(["negociateurs", "sites", "wilayas"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-mz-primary text-mz-primary"
                : "border-transparent text-mz-text-muted hover:text-mz-text"
            }`}
          >
            {t === "negociateurs" && <><Users size={13} className="inline mr-1" />Négociateurs</>}
            {t === "sites" && "Sites"}
            {t === "wilayas" && "Par wilaya"}
          </button>
        ))}
      </div>

      {/* Tab Négociateurs */}
      {tab === "negociateurs" && (
        <Table>
          <Thead>
            <Tr>
              <Th>Négociateur</Th>
              <Th>Contrat</Th>
              <Th>Total</Th>
              <Th>Bouclés</Th>
              <Th>En cours</Th>
              <Th>Bloqués</Th>
              <Th>Délai Doc B</Th>
              <Th>Loyer moy.</Th>
            </Tr>
          </Thead>
          <tbody>
            {negociateurs.map((n) => (
              <Tr key={n.negociateur}>
                <Td className="font-medium">{n.negociateur}</Td>
                <Td>
                  <span className={`text-xs rounded px-1.5 py-0.5 ${
                    n.type_contrat === "FREELANCE" ? "bg-purple-100 text-purple-700"
                    : n.type_contrat === "OPERATEUR" ? "bg-orange-100 text-orange-700"
                    : "bg-mz-surface-2 text-mz-text-muted"
                  }`}>
                    {n.type_contrat ?? "INTERNE"}
                  </span>
                </Td>
                <Td className="font-semibold">{n.total_sites}</Td>
                <Td><ProgressBar value={n.boucles} max={n.total_sites} color="bg-emerald-500" /></Td>
                <Td><ProgressBar value={n.en_cours} max={n.total_sites} color="bg-blue-500" /></Td>
                <Td><ProgressBar value={n.bloques} max={n.total_sites} color="bg-red-400" /></Td>
                <Td className="text-mz-text-muted text-sm">{fmt(n.delai_moyen_doc_b, " j")}</Td>
                <Td className="text-mz-text-muted text-sm">{fmt(n.loyer_moyen_da, " DA")}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      {/* Tab Sites */}
      {tab === "sites" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex gap-1">
              {["", "BOUCLE", "EN_COURS", "BLOQUE"].map((c) => (
                <button
                  key={c}
                  onClick={() => setCatFilter(c)}
                  className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                    catFilter === c
                      ? "bg-mz-primary text-white"
                      : "bg-mz-surface-2 text-mz-text-muted hover:bg-mz-border"
                  }`}
                >
                  {c === "" ? "Tous" : c === "BOUCLE" ? "Bouclés" : c === "EN_COURS" ? "En cours" : "Bloqués"}
                </button>
              ))}
            </div>
            <input
              placeholder="Négociateur…"
              value={negFilter}
              onChange={(e) => setNegFilter(e.target.value)}
              className="rounded-mz-md border border-mz-border bg-mz-input px-3 py-1.5 text-sm text-mz-text outline-none focus:border-mz-primary w-40"
            />
            <input
              placeholder="Wilaya…"
              value={wilayaFilter}
              onChange={(e) => setWilayaFilter(e.target.value)}
              className="rounded-mz-md border border-mz-border bg-mz-input px-3 py-1.5 text-sm text-mz-text outline-none focus:border-mz-primary w-40"
            />
            <span className="text-xs text-mz-text-muted ml-auto">{sitesTotal} site(s)</span>
          </div>
          <Table>
            <Thead>
              <Tr>
                <Th>Code</Th>
                <Th>Wilaya</Th>
                <Th>Propriétaire</Th>
                <Th>Négociateur</Th>
                <Th>Catégorie</Th>
                <Th>Avancement</Th>
                <Th>Loyer DA</Th>
                <Th>Doc B</Th>
                <Th>Délai</Th>
                <Th>Modèle</Th>
              </Tr>
            </Thead>
            <tbody>
              {sites.map((s) => (
                <Tr key={s.id}>
                  <Td className="font-mono text-xs font-medium text-mz-primary">{s.code}</Td>
                  <Td className="text-sm">{s.wilaya_name ?? s.commune_name ?? "—"}</Td>
                  <Td className="text-sm max-w-[160px] truncate">{s.owner_name ?? "—"}</Td>
                  <Td className="text-sm text-mz-text-muted">{s.negociateur_nom ?? "—"}</Td>
                  <Td><CategoryBadge cat={s.progress_category} /></Td>
                  <Td className="text-xs text-mz-text-muted max-w-[200px] truncate">{s.progress_raw ?? "—"}</Td>
                  <Td className="text-sm">{s.rent_negotiated ? s.rent_negotiated.toLocaleString("fr-DZ") : "—"}</Td>
                  <Td className="text-xs text-mz-text-muted">
                    {s.doc_b_date ? new Date(s.doc_b_date).toLocaleDateString("fr-DZ") : "—"}
                  </Td>
                  <Td className="text-sm">{s.doc_b_delay_days != null ? `${s.doc_b_delay_days} j` : "—"}</Td>
                  <Td className="text-xs text-mz-text-muted">{s.site_model ?? s.site_typology ?? "—"}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {/* Tab Wilayas */}
      {tab === "wilayas" && (
        <Table>
          <Thead>
            <Tr>
              <Th>Wilaya</Th>
              <Th>Total</Th>
              <Th>Bouclés</Th>
              <Th>En cours</Th>
              <Th>Bloqués</Th>
              <Th>Taux bouclage</Th>
            </Tr>
          </Thead>
          <tbody>
            {wilayas.map((w) => (
              <Tr key={w.wilaya}>
                <Td className="font-medium">{w.wilaya}</Td>
                <Td>{w.total}</Td>
                <Td><span className="text-emerald-600 font-medium">{w.boucles}</span></Td>
                <Td><span className="text-blue-600">{w.en_cours}</span></Td>
                <Td><span className="text-red-500">{w.bloques}</span></Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 rounded-full bg-mz-border overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${w.total > 0 ? Math.round((w.boucles / w.total) * 100) : 0}%` }}
                      />
                    </div>
                    <span className="text-xs text-mz-text-muted">
                      {w.total > 0 ? Math.round((w.boucles / w.total) * 100) : 0}%
                    </span>
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
