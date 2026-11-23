import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export type VisitType = "TSS" | "CCT";

export interface SiteVisit {
  id: string;
  visit_type: VisitType;
  visit_date: string;
  site_id: string | null;
  site_code: string;
  location: string | null;
  bet_name: string | null;
  radio_engineer_name: string | null;
  civil_work_name: string | null;
  transmission_name: string | null;
  negotiator_name: string | null;
  observation: string | null;
}

interface SiteOption {
  code: string;
  responsible_name: string | null;
}

interface UserOption {
  id: string;
  full_name: string;
}

interface Props {
  visit: SiteVisit | null; // null = création, sinon modification
  type: VisitType;
  date: string; // AAAA-MM-JJ, date proposée à la création
  onClose: () => void;
  onSaved: () => void;
}

interface FormState {
  visit_date: string;
  site_code: string;
  location: string;
  bet_name: string;
  radio_engineer_name: string;
  civil_work_name: string;
  transmission_name: string;
  negotiator_name: string;
  observation: string;
}

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

function toTextOrNull(value: string): string | null {
  const t = value.trim();
  return t ? t : null;
}

export default function SiteVisitModal({ visit, type, date, onClose, onSaved }: Props) {
  const isEdit = visit !== null;
  const isTss = type === "TSS";
  const title = isTss ? "TSS (Technical Site Survey)" : "CCT (Commission de Choix de Terrain)";

  const [form, setForm] = useState<FormState>({
    visit_date: visit?.visit_date ?? date,
    site_code: visit?.site_code ?? "",
    location: visit?.location ?? "",
    bet_name: visit?.bet_name ?? "",
    radio_engineer_name: visit?.radio_engineer_name ?? "",
    civil_work_name: visit?.civil_work_name ?? "",
    transmission_name: visit?.transmission_name ?? "",
    negotiator_name: visit?.negotiator_name ?? "",
    observation: visit?.observation ?? "",
  });
  // Le négociateur est pré-rempli d'après le site, tant que l'utilisateur ne l'a pas saisi lui-même
  const [negotiatorTouched, setNegotiatorTouched] = useState<boolean>(Boolean(visit?.negotiator_name));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [siteOptions, setSiteOptions] = useState<SiteOption[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);

  // Listes de suggestions (non bloquant si l'une échoue)
  useEffect(() => {
    api
      .get<SiteOption[]>("/site-visits/site-options")
      .then(({ data }) => setSiteOptions(data))
      .catch(() => setSiteOptions([]));
    api
      .get<UserOption[]>("/users/options")
      .then(({ data }) => setUsers(data))
      .catch(() => setUsers([]));
  }, []);

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
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  function onSiteCodeChange(e: ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setForm((f) => {
      const next = { ...f, site_code: value };
      if (!negotiatorTouched) {
        const match = siteOptions.find((s) => s.code.toUpperCase() === value.trim().toUpperCase());
        next.negotiator_name = match?.responsible_name ?? "";
      }
      return next;
    });
  }

  function onNegotiatorChange(e: ChangeEvent<HTMLInputElement>) {
    setNegotiatorTouched(true);
    setForm((f) => ({ ...f, negotiator_name: e.target.value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!form.site_code.trim()) {
      setError("Indiquez le code du site.");
      return;
    }
    if (!form.visit_date) {
      setError("Indiquez la date.");
      return;
    }

    const payload = {
      visit_type: type,
      visit_date: form.visit_date,
      site_code: form.site_code.trim(),
      location: toTextOrNull(form.location),
      bet_name: toTextOrNull(form.bet_name),
      radio_engineer_name: isTss ? toTextOrNull(form.radio_engineer_name) : null,
      civil_work_name: toTextOrNull(form.civil_work_name),
      transmission_name: toTextOrNull(form.transmission_name),
      negotiator_name: toTextOrNull(form.negotiator_name),
      observation: toTextOrNull(form.observation),
    };

    setIsSaving(true);
    try {
      if (visit) {
        await api.patch(`/site-visits/${visit.id}`, payload);
      } else {
        await api.post("/site-visits", payload);
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
      aria-label={isEdit ? `Modifier la ${type}` : `Ajouter une ${type}`}
    >
      <Card className="max-h-[90vh] w-full max-w-xl overflow-y-auto">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-mz-text">
            {isEdit ? "Modifier la" : "Ajouter une"} {title}
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="visit-date" className={LABEL_CLASS}>
                Date *
              </label>
              <input
                id="visit-date"
                type="date"
                className={INPUT_CLASS}
                value={form.visit_date}
                onChange={set("visit_date")}
                required
              />
            </div>
            <div>
              <label htmlFor="visit-code" className={LABEL_CLASS}>
                Code site *
              </label>
              <input
                id="visit-code"
                className={INPUT_CLASS}
                value={form.site_code}
                onChange={onSiteCodeChange}
                list="visit-site-codes"
                autoComplete="off"
                placeholder="Ex. AL2120"
                required
              />
              <datalist id="visit-site-codes">
                {siteOptions.map((s) => (
                  <option key={s.code} value={s.code} />
                ))}
              </datalist>
            </div>

            {!isTss && (
              <div className="sm:col-span-2">
                <label htmlFor="visit-location" className={LABEL_CLASS}>
                  Lieu de rencontre
                </label>
                <input id="visit-location" className={INPUT_CLASS} value={form.location} onChange={set("location")} />
              </div>
            )}

            <div>
              <label htmlFor="visit-bet" className={LABEL_CLASS}>
                {isTss ? "BET présent (nom)" : "BET (nom)"}
              </label>
              <input id="visit-bet" className={INPUT_CLASS} value={form.bet_name} onChange={set("bet_name")} />
            </div>

            {isTss && (
              <div>
                <label htmlFor="visit-radio" className={LABEL_CLASS}>
                  Ingénieur Radio présent (nom)
                </label>
                <input
                  id="visit-radio"
                  className={INPUT_CLASS}
                  value={form.radio_engineer_name}
                  onChange={set("radio_engineer_name")}
                />
              </div>
            )}

            <div>
              <label htmlFor="visit-civil" className={LABEL_CLASS}>
                Civil Work présent (nom)
              </label>
              <input
                id="visit-civil"
                className={INPUT_CLASS}
                value={form.civil_work_name}
                onChange={set("civil_work_name")}
              />
            </div>
            <div>
              <label htmlFor="visit-transmission" className={LABEL_CLASS}>
                {isTss ? "Transmission présent (nom)" : "Transmission (nom)"}
              </label>
              <input
                id="visit-transmission"
                className={INPUT_CLASS}
                value={form.transmission_name}
                onChange={set("transmission_name")}
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="visit-negotiator" className={LABEL_CLASS}>
                Négociateur (nom)
              </label>
              <input
                id="visit-negotiator"
                className={INPUT_CLASS}
                value={form.negotiator_name}
                onChange={onNegotiatorChange}
                list="visit-people"
                autoComplete="off"
              />
              <datalist id="visit-people">
                {users.map((u) => (
                  <option key={u.id} value={u.full_name} />
                ))}
              </datalist>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="visit-obs" className={LABEL_CLASS}>
                Observation
              </label>
              <textarea
                id="visit-obs"
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
              {isSaving ? "Enregistrement..." : isEdit ? "Enregistrer" : "Ajouter"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
