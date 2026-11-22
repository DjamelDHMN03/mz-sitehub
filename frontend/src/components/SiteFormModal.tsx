import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export interface StatusOption {
  id: number;
  label: string;
}

interface Props {
  siteId: string | null; // null = création, sinon modification
  statuses: StatusOption[];
  onClose: () => void;
  onSaved: () => void;
}

interface FormState {
  code: string;
  name: string;
  status_id: string;
  priority: string;
  address: string;
  latitude: string;
  longitude: string;
  site_type: string;
  owner_name: string;
  organisme: string;
  next_action: string;
  observation: string;
}

interface SiteFull {
  code: string;
  name: string | null;
  status_id: number;
  priority: number;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  site_type: string | null;
  owner_name: string | null;
  organisme: string | null;
  next_action: string | null;
  observation: string | null;
}

const EMPTY_FORM: FormState = {
  code: "",
  name: "",
  status_id: "",
  priority: "2",
  address: "",
  latitude: "",
  longitude: "",
  site_type: "",
  owner_name: "",
  organisme: "",
  next_action: "",
  observation: "",
};

const INPUT_CLASS =
  "w-full rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary disabled:opacity-60";
const LABEL_CLASS = "mb-1 block text-xs font-medium text-mz-text-muted";

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (d as { msg?: string }).msg ?? "Champ invalide").join(" ; ");
  }
  return "Une erreur est survenue. Réessayez.";
}

function toNumberOrNull(value: string): number | null {
  const t = value.trim().replace(",", ".");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function toTextOrNull(value: string): string | null {
  const t = value.trim();
  return t ? t : null;
}

export default function SiteFormModal({ siteId, statuses, onClose, onSaved }: Props) {
  const isEdit = siteId !== null;
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modification : on recharge le site complet pour pré-remplir le formulaire
  useEffect(() => {
    if (!siteId) return;
    setIsLoading(true);
    api
      .get<SiteFull>(`/sites/${siteId}`)
      .then(({ data }) => {
        setForm({
          code: data.code,
          name: data.name ?? "",
          status_id: String(data.status_id),
          priority: String(data.priority),
          address: data.address ?? "",
          latitude: data.latitude !== null ? String(data.latitude) : "",
          longitude: data.longitude !== null ? String(data.longitude) : "",
          site_type: data.site_type ?? "",
          owner_name: data.owner_name ?? "",
          organisme: data.organisme ?? "",
          next_action: data.next_action ?? "",
          observation: data.observation ?? "",
        });
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setIsLoading(false));
  }, [siteId]);

  // Création : statut par défaut = premier de la liste
  useEffect(() => {
    if (isEdit) return;
    if (statuses.length > 0) {
      setForm((f) => (f.status_id ? f : { ...f, status_id: String(statuses[0].id) }));
    }
  }, [isEdit, statuses]);

  // Fermeture avec Échap
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !isSaving) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, isSaving]);

  const set =
    (key: keyof FormState) =>
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!isEdit && form.code.trim().length < 2) {
      setError("Le code du site doit contenir au moins 2 caractères.");
      return;
    }
    if (!form.status_id) {
      setError("Choisissez un statut.");
      return;
    }

    const lat = toNumberOrNull(form.latitude);
    const lon = toNumberOrNull(form.longitude);
    if ((form.latitude.trim() && lat === null) || (form.longitude.trim() && lon === null)) {
      setError("Coordonnées invalides : utilisez le format décimal (ex. 36.7538).");
      return;
    }
    if ((lat === null) !== (lon === null)) {
      setError("Renseignez la latitude et la longitude ensemble.");
      return;
    }
    if (lat !== null && lon !== null && (lat < 18.5 || lat > 38 || lon < -9 || lon > 12.5)) {
      setError("Ces coordonnées sont en dehors de l'Algérie. Vérifiez la latitude et la longitude.");
      return;
    }

    const common = {
      name: toTextOrNull(form.name),
      status_id: Number(form.status_id),
      priority: Number(form.priority),
      address: toTextOrNull(form.address),
      latitude: lat,
      longitude: lon,
      site_type: toTextOrNull(form.site_type),
      owner_name: toTextOrNull(form.owner_name),
      organisme: toTextOrNull(form.organisme),
      next_action: toTextOrNull(form.next_action),
      observation: toTextOrNull(form.observation),
    };

    setIsSaving(true);
    try {
      if (isEdit) {
        await api.patch(`/sites/${siteId}`, common);
      } else {
        await api.post("/sites", { code: form.code.trim(), ...common });
      }
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={isEdit ? "Modifier le site" : "Ajouter un site"}
    >
      <Card className="max-h-[90vh] w-full max-w-2xl overflow-y-auto">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-mz-text">
            {isEdit ? `Modifier le site ${form.code}` : "Ajouter un site"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Fermer"
            className="rounded-mz-md p-1 text-mz-text-muted hover:text-mz-text focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary"
          >
            <X size={18} />
          </button>
        </div>

        {isLoading ? (
          <p className="text-sm text-mz-text-muted">Chargement...</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="site-code" className={LABEL_CLASS}>
                  Code du site *
                </label>
                <input
                  id="site-code"
                  className={INPUT_CLASS}
                  value={form.code}
                  onChange={set("code")}
                  disabled={isEdit}
                  maxLength={32}
                  required
                />
                {isEdit && (
                  <p className="mt-1 text-xs text-mz-text-muted">Le code ne se modifie pas ici.</p>
                )}
              </div>
              <div>
                <label htmlFor="site-name" className={LABEL_CLASS}>
                  Nom du site
                </label>
                <input id="site-name" className={INPUT_CLASS} value={form.name} onChange={set("name")} />
              </div>
              <div>
                <label htmlFor="site-status" className={LABEL_CLASS}>
                  Statut *
                </label>
                <select
                  id="site-status"
                  className={INPUT_CLASS}
                  value={form.status_id}
                  onChange={set("status_id")}
                  required
                >
                  {statuses.length === 0 && <option value="">Chargement...</option>}
                  {statuses.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="site-priority" className={LABEL_CLASS}>
                  Priorité
                </label>
                <select
                  id="site-priority"
                  className={INPUT_CLASS}
                  value={form.priority}
                  onChange={set("priority")}
                >
                  <option value="1">1 - Haute</option>
                  <option value="2">2 - Normale</option>
                  <option value="3">3 - Basse</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="site-address" className={LABEL_CLASS}>
                  Adresse
                </label>
                <input
                  id="site-address"
                  className={INPUT_CLASS}
                  value={form.address}
                  onChange={set("address")}
                />
              </div>
              <div>
                <label htmlFor="site-lat" className={LABEL_CLASS}>
                  Latitude (décimal)
                </label>
                <input
                  id="site-lat"
                  className={INPUT_CLASS}
                  value={form.latitude}
                  onChange={set("latitude")}
                  inputMode="decimal"
                  placeholder="36.7538"
                />
              </div>
              <div>
                <label htmlFor="site-lon" className={LABEL_CLASS}>
                  Longitude (décimal)
                </label>
                <input
                  id="site-lon"
                  className={INPUT_CLASS}
                  value={form.longitude}
                  onChange={set("longitude")}
                  inputMode="decimal"
                  placeholder="3.0588"
                />
              </div>
              <div>
                <label htmlFor="site-type" className={LABEL_CLASS}>
                  Type de site
                </label>
                <input
                  id="site-type"
                  className={INPUT_CLASS}
                  value={form.site_type}
                  onChange={set("site_type")}
                />
              </div>
              <div>
                <label htmlFor="site-organisme" className={LABEL_CLASS}>
                  Organisme
                </label>
                <input
                  id="site-organisme"
                  className={INPUT_CLASS}
                  value={form.organisme}
                  onChange={set("organisme")}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="site-owner" className={LABEL_CLASS}>
                  Propriétaire
                </label>
                <input
                  id="site-owner"
                  className={INPUT_CLASS}
                  value={form.owner_name}
                  onChange={set("owner_name")}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="site-next" className={LABEL_CLASS}>
                  Prochaine action
                </label>
                <input
                  id="site-next"
                  className={INPUT_CLASS}
                  value={form.next_action}
                  onChange={set("next_action")}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="site-obs" className={LABEL_CLASS}>
                  Observation
                </label>
                <textarea
                  id="site-obs"
                  rows={3}
                  className={INPUT_CLASS}
                  value={form.observation}
                  onChange={set("observation")}
                />
              </div>
            </div>

            {error && <p className="text-sm text-mz-danger">{error}</p>}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
                Annuler
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? "Enregistrement..." : isEdit ? "Enregistrer" : "Créer le site"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}