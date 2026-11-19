import { ReactNode, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/Button";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusBadge } from "@/components/Badge";
import { ArrowLeft, Check, ExternalLink, Pencil, Star, X } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface SiteFull {
  id: string;
  code: string;
  previous_codes: string[];
  name: string | null;
  wilaya_id: number | null;
  commune_id: number | null;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  site_type: string | null;
  owner_name: string | null;
  organisme: string | null;
  status_id: number;
  priority: number;
  observation: string | null;
  is_favorite: boolean;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface StatusOut {
  id: number;
  code: string;
  label: string;
  color: string;
}

interface Wilaya {
  id: number;
  name: string;
}

interface Commune {
  id: number;
  wilaya_id: number;
  daira: string | null;
  name: string;
}

type Kind = "text" | "number" | "date" | "textarea";
type ColKey = "name" | "owner_name" | "organisme" | "address" | "site_type" | "observation" | "latitude" | "longitude";

interface FieldDef {
  id: string; // identifiant du champ dans le formulaire
  label: string;
  kind: Kind;
  col?: ColKey; // colonne de la table sites
  cf?: string; // clé dans custom_fields
  wide?: boolean;
}

// ---------------------------------------------------------------------------
// Les 29 colonnes du suivi Excel, réparties par rubrique
// ---------------------------------------------------------------------------
const F_GENERAL: FieldDef[] = [
  { id: "name", label: "Nom du site", kind: "text", col: "name" },
  { id: "owner_name", label: "Nom du candidat", kind: "text", col: "owner_name" },
  { id: "organisme", label: "Organisme propriétaire", kind: "text", col: "organisme" },
  { id: "cf.type_propriete", label: "Type de propriété", kind: "text", cf: "type_propriete" },
  { id: "cf.telephone", label: "Téléphone", kind: "text", cf: "telephone" },
  { id: "cf.projet", label: "Projet", kind: "text", cf: "projet" },
  { id: "cf.etat", label: "État", kind: "text", cf: "etat" },
  { id: "cf.acquisition", label: "Acquisition", kind: "text", cf: "acquisition" },
  { id: "cf.charge_acquisition", label: "Chargé d'acquisition", kind: "text", cf: "charge_acquisition" },
  { id: "cf.region", label: "Région", kind: "text", cf: "region" },
  { id: "address", label: "Adresse", kind: "textarea", col: "address", wide: true },
];

const F_FINANCE: FieldDef[] = [
  { id: "cf.loyer_negocie", label: "Loyer négocié (DA)", kind: "number", cf: "loyer_negocie" },
];

const F_GEO: FieldDef[] = [
  { id: "latitude", label: "Latitude GPS", kind: "number", col: "latitude" },
  { id: "longitude", label: "Longitude GPS", kind: "number", col: "longitude" },
  { id: "cf.gps_lat_nominal", label: "Latitude point nominal", kind: "number", cf: "gps_lat_nominal" },
  { id: "cf.gps_long_nominal", label: "Longitude point nominal", kind: "number", cf: "gps_long_nominal" },
];

const F_DOSSIER: FieldDef[] = [
  { id: "cf.avancement", label: "Avancement", kind: "text", cf: "avancement" },
  { id: "cf.doc_a_date", label: "Doc A (date)", kind: "date", cf: "doc_a_date" },
  { id: "cf.doc_b_date", label: "Doc B (date)", kind: "date", cf: "doc_b_date" },
  { id: "cf.delai_doc_b_jours", label: "Délai Doc B (jours)", kind: "number", cf: "delai_doc_b_jours" },
  { id: "cf.tss_date", label: "TSS (date)", kind: "date", cf: "tss_date" },
  { id: "cf.contrat_date", label: "Contrat (date)", kind: "date", cf: "contrat_date" },
  { id: "cf.contrat_statut", label: "Contrat (statut)", kind: "text", cf: "contrat_statut" },
  { id: "cf.rapport_zone", label: "Rapport de zone", kind: "text", cf: "rapport_zone" },
];

const F_TECH: FieldDef[] = [
  { id: "site_type", label: "Typologie du site", kind: "text", col: "site_type" },
  { id: "cf.type_site", label: "Type de site", kind: "text", cf: "type_site" },
];

const F_REMARQUES: FieldDef[] = [
  { id: "observation", label: "Remarques", kind: "textarea", col: "observation", wide: true },
];

// Textes de repli quand les wilayas/communes ne sont pas encore saisies dans la base
const F_GEO_TEXT: FieldDef[] = [
  { id: "cf.wilaya_texte", label: "Wilaya (texte)", kind: "text", cf: "wilaya_texte" },
  { id: "cf.commune_texte", label: "Commune (texte)", kind: "text", cf: "commune_texte" },
];

const ALL_FIELDS: FieldDef[] = [
  ...F_GENERAL,
  ...F_FINANCE,
  ...F_GEO,
  ...F_DOSSIER,
  ...F_TECH,
  ...F_REMARQUES,
  ...F_GEO_TEXT,
];

const INPUT_CLASS =
  "w-full rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary";

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------
type Draft = Record<string, string>;

function readField(site: SiteFull, f: FieldDef): string {
  let raw: unknown = null;
  if (f.col) raw = site[f.col];
  else if (f.cf) raw = site.custom_fields[f.cf];
  if (f.id === "observation" && (raw === null || raw === "")) raw = site.custom_fields["remarques"];
  return raw === null || raw === undefined ? "" : String(raw);
}

function buildDraft(site: SiteFull): Draft {
  const d: Draft = {};
  for (const f of ALL_FIELDS) d[f.id] = readField(site, f);
  d["wilaya_id"] = site.wilaya_id === null ? "" : String(site.wilaya_id);
  d["commune_id"] = site.commune_id === null ? "" : String(site.commune_id);
  d["status_id"] = String(site.status_id);
  d["priority"] = String(site.priority);
  return d;
}

function toNumber(s: string): number | null {
  const t = s.trim().replace(",", ".");
  if (t === "") return null;
  const n = Number(t);
  return Number.isNaN(n) ? Number.NaN : n;
}

function haversineMetres(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const rad = (x: number) => (x * Math.PI) / 180;
  const a =
    Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.sqrt(a));
}

function inAlgeria(lat: number, lon: number): boolean {
  return lat >= 18.5 && lat <= 38 && lon >= -9 && lon <= 12.5;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("fr-FR");
}

function messageErreur(e: unknown): string {
  const err = e as { response?: { status?: number; data?: { detail?: unknown } } };
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (err.response?.status === 403) return "Vous n'avez pas le droit de modifier cette fiche.";
  if (err.response?.status === 404) return "Ce site est introuvable (il a peut-être été supprimé).";
  return "Une erreur est survenue. Vérifiez que le serveur est joignable.";
}

// ---------------------------------------------------------------------------
// Composants d'affichage
// ---------------------------------------------------------------------------
function Field({
  def,
  draft,
  editing,
  onChange,
  display,
}: {
  def: FieldDef;
  draft: Draft;
  editing: boolean;
  onChange: (id: string, v: string) => void;
  display?: string;
}) {
  const value = draft[def.id] ?? "";
  return (
    <div className={def.wide ? "md:col-span-2" : ""}>
      <p className="mb-1 text-xs font-medium text-mz-text-muted">{def.label}</p>
      {editing ? (
        def.kind === "textarea" ? (
          <textarea
            rows={3}
            value={value}
            onChange={(e) => onChange(def.id, e.target.value)}
            className={INPUT_CLASS}
          />
        ) : (
          <input
            type={def.kind === "date" ? "date" : "text"}
            inputMode={def.kind === "number" ? "decimal" : undefined}
            value={value}
            onChange={(e) => onChange(def.id, e.target.value)}
            className={INPUT_CLASS}
          />
        )
      ) : (
        <p className="whitespace-pre-wrap text-sm text-mz-text">
          {display ?? (value !== "" ? value : <span className="text-mz-text-disabled">À COMPLÉTER</span>)}
        </p>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{children}</div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const canEdit = user !== null && user.role_code !== "LECTURE";

  const [site, setSite] = useState<SiteFull | null>(null);
  const [statuses, setStatuses] = useState<StatusOut[]>([]);
  const [wilayas, setWilayas] = useState<Wilaya[]>([]);
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Draft>({});

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const { data } = await api.get<SiteFull>(`/sites/${id}`);
      setSite(data);
      setDraft(buildDraft(data));
      setError(null);
    } catch (e) {
      setError(messageErreur(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Listes de référence : si elles échouent ou sont vides, la fiche reste utilisable
  useEffect(() => {
    api.get<StatusOut[]>("/site-statuses").then(({ data }) => setStatuses(data)).catch(() => undefined);
    api.get<Wilaya[]>("/geography/wilayas").then(({ data }) => setWilayas(data)).catch(() => undefined);
  }, []);

  const wilayaCourante = editing ? draft["wilaya_id"] : site?.wilaya_id != null ? String(site.wilaya_id) : "";
  useEffect(() => {
    if (!wilayaCourante) {
      setCommunes([]);
      return;
    }
    api
      .get<Commune[]>("/geography/communes", { params: { wilaya_id: Number(wilayaCourante) } })
      .then(({ data }) => setCommunes(data))
      .catch(() => setCommunes([]));
  }, [wilayaCourante]);

  function setField(fieldId: string, value: string) {
    setDraft((prev) => {
      const next = { ...prev, [fieldId]: value };
      if (fieldId === "wilaya_id") next["commune_id"] = "";
      return next;
    });
  }

  function startEdit() {
    if (!site) return;
    setDraft(buildDraft(site));
    setNotice(null);
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    if (site) setDraft(buildDraft(site));
    setError(null);
    setEditing(false);
  }

  async function save() {
    if (!site || !id) return;
    setError(null);
    setSaving(true);
    try {
      // Protection contre l'écrasement : la fiche a-t-elle changé depuis son ouverture ?
      const fresh = (await api.get<SiteFull>(`/sites/${id}`)).data;
      if (fresh.updated_at !== site.updated_at) {
        setError(
          "Cette fiche a été modifiée par quelqu'un d'autre depuis que vous l'avez ouverte. " +
            "Cliquez sur « Annuler », la fiche se recharge avec les dernières modifications, puis refaites votre changement."
        );
        setSite(fresh);
        return;
      }

      const before = buildDraft(site);
      const payload: Record<string, unknown> = {};
      const cf: Record<string, unknown> = { ...fresh.custom_fields };
      let cfChanged = false;

      for (const f of ALL_FIELDS) {
        if (draft[f.id] === before[f.id]) continue;
        if (f.col === "latitude" || f.col === "longitude") continue; // traités ensemble ci-dessous
        let value: string | number | null;
        if (f.kind === "number") {
          const n = toNumber(draft[f.id]);
          if (Number.isNaN(n)) {
            setError(`Valeur numérique invalide pour « ${f.label} ».`);
            return;
          }
          value = n;
        } else {
          const t = draft[f.id].trim();
          value = t === "" ? null : t;
        }
        if (f.col) payload[f.col] = value;
        else if (f.cf) {
          if (value === null) delete cf[f.cf];
          else cf[f.cf] = value;
          cfChanged = true;
        }
      }
      // Les points nominaux (custom_fields) sont validés comme des coordonnées
      for (const key of ["cf.gps_lat_nominal", "cf.gps_long_nominal"]) {
        const n = toNumber(draft[key] ?? "");
        if (Number.isNaN(n)) {
          setError("Coordonnée du point nominal invalide.");
          return;
        }
      }

      // GPS : latitude et longitude partent toujours ensemble
      if (draft["latitude"] !== before["latitude"] || draft["longitude"] !== before["longitude"]) {
        const lat = toNumber(draft["latitude"]);
        const lon = toNumber(draft["longitude"]);
        if (Number.isNaN(lat) || Number.isNaN(lon)) {
          setError("Latitude ou longitude invalide : utilisez des degrés décimaux (exemple 36.7101).");
          return;
        }
        if ((lat === null) !== (lon === null)) {
          setError("Renseignez la latitude ET la longitude (ou laissez les deux vides).");
          return;
        }
        if (lat !== null && lon !== null) {
          if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            setError("Coordonnées hors limites. Latitude entre -90 et 90, longitude entre -180 et 180.");
            return;
          }
          if (!inAlgeria(lat, lon)) {
            const ok = window.confirm(
              "Ces coordonnées sont en dehors de l'Algérie. Vérifiez que la latitude et la longitude ne sont pas inversées. Enregistrer quand même ?"
            );
            if (!ok) return;
          }
        }
        payload["latitude"] = lat;
        payload["longitude"] = lon;
      }

      // Listes déroulantes
      if (draft["status_id"] !== before["status_id"]) payload["status_id"] = Number(draft["status_id"]);
      if (draft["priority"] !== before["priority"]) payload["priority"] = Number(draft["priority"]);
      if (draft["wilaya_id"] !== before["wilaya_id"])
        payload["wilaya_id"] = draft["wilaya_id"] === "" ? null : Number(draft["wilaya_id"]);
      if (draft["commune_id"] !== before["commune_id"])
        payload["commune_id"] = draft["commune_id"] === "" ? null : Number(draft["commune_id"]);

      // custom_fields est remplacé en bloc par l'API : on renvoie l'ensemble fusionné
      if (cfChanged) payload["custom_fields"] = cf;

      if (Object.keys(payload).length === 0) {
        setEditing(false);
        setNotice("Aucune modification à enregistrer.");
        return;
      }

      const { data } = await api.patch<SiteFull>(`/sites/${id}`, payload);
      setSite(data);
      setDraft(buildDraft(data));
      setEditing(false);
      setNotice("Modifications enregistrées.");
    } catch (e) {
      setError(messageErreur(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading && !site) return <p className="text-sm text-mz-text-muted">Chargement...</p>;
  if (!site) {
    return (
      <div className="space-y-3">
        <Link to="/sites" className="inline-flex items-center gap-1 text-sm text-mz-primary hover:underline">
          <ArrowLeft size={14} /> Retour aux sites
        </Link>
        <p className="text-sm text-mz-danger">{error ?? "Site introuvable."}</p>
      </div>
    );
  }

  const status = statuses.find((s) => s.id === Number(editing ? draft["status_id"] : site.status_id));
  const lat = toNumber(draft["latitude"] ?? "");
  const lon = toNumber(draft["longitude"] ?? "");
  const nLat = toNumber(draft["cf.gps_lat_nominal"] ?? "");
  const nLon = toNumber(draft["cf.gps_long_nominal"] ?? "");
  const gps = lat !== null && lon !== null && !Number.isNaN(lat) && !Number.isNaN(lon) ? { lat, lon } : null;
  const nominal =
    nLat !== null && nLon !== null && !Number.isNaN(nLat) && !Number.isNaN(nLon) ? { lat: nLat, lon: nLon } : null;
  const mapsUrl = gps ? `https://www.google.com/maps?q=${gps.lat},${gps.lon}` : null;
  const deltaMetres = gps && nominal ? haversineMetres(gps.lat, gps.lon, nominal.lat, nominal.lon) : null;

  const wilayaNom =
    wilayas.find((w) => w.id === site.wilaya_id)?.name ?? String(site.custom_fields["wilaya_texte"] ?? "");
  const communeNom =
    communes.find((c) => c.id === site.commune_id)?.name ?? String(site.custom_fields["commune_texte"] ?? "");

  const common = { draft, editing, onChange: setField };
  const textDef = (fid: string): FieldDef => F_GEO_TEXT.find((f) => f.id === fid) as FieldDef;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/sites" className="inline-flex items-center gap-1 text-sm text-mz-primary hover:underline">
            <ArrowLeft size={14} /> Sites
          </Link>
          <h2 className="text-xl font-semibold text-mz-text">{site.code}</h2>
          {site.is_favorite && <Star size={16} className="fill-mz-warning text-mz-warning" />}
          {status && <StatusBadge label={status.label} color={status.color} />}
        </div>
        <div className="flex items-center gap-2">
          {mapsUrl && (
            <a href={mapsUrl} target="_blank" rel="noreferrer">
              <Button variant="secondary" type="button">
                <ExternalLink size={14} /> Google Maps
              </Button>
            </a>
          )}
          {canEdit && !editing && (
            <Button type="button" onClick={startEdit}>
              <Pencil size={14} /> Modifier
            </Button>
          )}
          {editing && (
            <>
              <Button type="button" onClick={() => void save()} disabled={saving}>
                <Check size={14} /> {saving ? "Enregistrement..." : "Enregistrer"}
              </Button>
              <Button type="button" variant="ghost" onClick={cancelEdit} disabled={saving}>
                <X size={14} /> Annuler
              </Button>
            </>
          )}
        </div>
      </div>

      {error && (
        <p className="rounded-mz-md border border-mz-danger/40 bg-mz-danger/10 px-3 py-2 text-sm text-mz-danger">{error}</p>
      )}
      {notice && (
        <p className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm text-mz-text">{notice}</p>
      )}

      <Section title="Informations générales">
        {F_GENERAL.slice(0, 5).map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}

        {/* Statut d'acquisition et priorité */}
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Statut d'acquisition</p>
          {editing ? (
            <select value={draft["status_id"]} onChange={(e) => setField("status_id", e.target.value)} className={INPUT_CLASS}>
              {statuses.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-mz-text">{status ? status.label : `#${site.status_id}`}</p>
          )}
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Priorité</p>
          {editing ? (
            <select value={draft["priority"]} onChange={(e) => setField("priority", e.target.value)} className={INPUT_CLASS}>
              <option value="1">1 - Haute</option>
              <option value="2">2 - Normale</option>
              <option value="3">3 - Basse</option>
            </select>
          ) : (
            <p className="text-sm text-mz-text">{site.priority}</p>
          )}
        </div>

        {F_GENERAL.slice(5, 10).map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}

        {/* Wilaya : liste si disponible, sinon texte */}
        {editing && wilayas.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium text-mz-text-muted">Wilaya</p>
            <select value={draft["wilaya_id"]} onChange={(e) => setField("wilaya_id", e.target.value)} className={INPUT_CLASS}>
              <option value="">— Non renseignée —</option>
              {wilayas.map((w) => (
                <option key={w.id} value={w.id}>
                  {String(w.id).padStart(2, "0")} - {w.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <Field def={textDef("cf.wilaya_texte")} {...common} display={editing ? undefined : wilayaNom || undefined} />
        )}

        {/* Commune : liste si disponible, sinon texte */}
        {editing && communes.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium text-mz-text-muted">Commune</p>
            <select value={draft["commune_id"]} onChange={(e) => setField("commune_id", e.target.value)} className={INPUT_CLASS}>
              <option value="">— Non renseignée —</option>
              {communes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <Field def={textDef("cf.commune_texte")} {...common} display={editing ? undefined : communeNom || undefined} />
        )}

        {F_GENERAL.slice(10).map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}
      </Section>

      <Section title="Informations financières">
        {F_FINANCE.map((f) => (
          <Field
            key={f.id}
            def={f}
            {...common}
            display={
              !editing && draft[f.id] !== "" && !Number.isNaN(Number(draft[f.id]))
                ? `${Number(draft[f.id]).toLocaleString("fr-FR")} DA`
                : undefined
            }
          />
        ))}
      </Section>

      <Section title="Géographie">
        {F_GEO.map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Écart point nominal / GPS (calculé)</p>
          <p className="text-sm text-mz-text">
            {deltaMetres !== null ? `${Math.round(deltaMetres).toLocaleString("fr-FR")} m` : "—"}
          </p>
        </div>
        <div className="md:col-span-2">
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Lien Google Maps (généré)</p>
          <p className="break-all text-sm text-mz-text">{mapsUrl ?? "Renseignez la latitude et la longitude GPS."}</p>
        </div>
      </Section>

      <Section title="Dossier et suivi">
        {F_DOSSIER.map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}
      </Section>

      <Section title="Informations techniques">
        {F_TECH.map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}
      </Section>

      <Section title="Remarques">
        {F_REMARQUES.map((f) => (
          <Field key={f.id} def={f} {...common} />
        ))}
      </Section>

      <Section title="Traçabilité">
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Créé le</p>
          <p className="text-sm text-mz-text">{formatDate(site.created_at)}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Dernière modification</p>
          <p className="text-sm text-mz-text">{formatDate(site.updated_at)}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-mz-text-muted">Origine des données importées</p>
          <p className="text-sm text-mz-text">{String(site.custom_fields["import_source"] ?? "Saisie manuelle")}</p>
        </div>
        {site.custom_fields["avancement_origine"] !== undefined && (
          <div>
            <p className="mb-1 text-xs font-medium text-mz-text-muted">Avancement (texte Excel d'origine)</p>
            <p className="text-sm text-mz-text">{String(site.custom_fields["avancement_origine"])}</p>
          </div>
        )}
        {site.previous_codes.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium text-mz-text-muted">Anciens codes</p>
            <p className="text-sm text-mz-text">{site.previous_codes.join(", ")}</p>
          </div>
        )}
      </Section>
    </div>
  );
}
