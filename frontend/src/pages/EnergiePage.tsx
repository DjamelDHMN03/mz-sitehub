import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { CheckCircle2, X, Zap } from "lucide-react";
import { api } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Configuration                                                       */
/* ------------------------------------------------------------------ */

// Si les autres pages appellent le backend sans le préfixe /api
// (ex. "/chat/messages"), remplacez cette valeur par "/energie/sites".
const BASE = "/api/energie/sites";
const MONTANT_DEFAUT = 18000;

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type Mode = "SONELGAZ" | "SOUS_COMPTAGE";
type Etape = "NON_DEMARRE" | "DEMANDE" | "ETUDE" | "DEVIS" | "RACCORDE";

interface SiteEnergie {
  site_id: string;
  code_site: string;
  nom_site: string | null;
  adresse: string | null;
  mode: Mode;
  demande_deposee: boolean;
  demande_deposee_le: string | null;
  etude_effectuee: boolean;
  etude_effectuee_le: string | null;
  devis_paye: boolean;
  devis_paye_le: string | null;
  site_raccorde: boolean;
  site_raccorde_le: string | null;
  sous_comptage_permanent: boolean;
  provisoire_actif: boolean;
  provisoire_debut: string | null;
  provisoire_fin: string | null;
  montant_mensuel: number;
  observation: string | null;
}

interface Paiement {
  id: string;
  mois: string;
  date_paiement: string;
  montant: number;
  observation: string | null;
}

interface FormulaireSite {
  mode: Mode;
  demande_deposee: boolean;
  demande_deposee_le: string;
  etude_effectuee: boolean;
  etude_effectuee_le: string;
  devis_paye: boolean;
  devis_paye_le: string;
  site_raccorde: boolean;
  site_raccorde_le: string;
  sous_comptage_permanent: boolean;
  provisoire_actif: boolean;
  provisoire_debut: string;
  provisoire_fin: string;
  montant_mensuel: string;
  observation: string;
}

type PaiementsParSite = Record<string, Paiement[]>;
type Brut = Record<string, unknown>;

/* ------------------------------------------------------------------ */
/* Utilitaires de lecture des réponses du backend                      */
/* ------------------------------------------------------------------ */

function enObjet(valeur: unknown): Brut {
  return typeof valeur === "object" && valeur !== null ? (valeur as Brut) : {};
}

function texte(valeur: unknown): string | null {
  return typeof valeur === "string" && valeur !== "" ? valeur : null;
}

function booleen(valeur: unknown): boolean {
  return valeur === true;
}

function nombre(valeur: unknown, defaut: number): number {
  if (typeof valeur === "number" && Number.isFinite(valeur)) {
    return valeur;
  }
  if (typeof valeur === "string" && valeur.trim() !== "" && Number.isFinite(Number(valeur))) {
    return Number(valeur);
  }
  return defaut;
}

function dateCourte(valeur: unknown): string | null {
  const t = texte(valeur);
  return t === null ? null : t.slice(0, 10);
}

// Accepte aussi bien une réponse de type axios ({ data: ... }) qu'une
// réponse déjà dépouillée.
function extraire(reponse: unknown): unknown {
  if (typeof reponse === "object" && reponse !== null && "data" in reponse) {
    return (reponse as { data: unknown }).data;
  }
  return reponse;
}

function messageErreur(err: unknown): string {
  if (typeof err === "object" && err !== null) {
    const e = err as { response?: { data?: { detail?: unknown } }; message?: unknown };
    const detail = e.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (typeof e.message === "string") {
      return e.message;
    }
  }
  return "Une erreur est survenue.";
}

function normaliserSite(brut: unknown): SiteEnergie {
  const b = enObjet(brut);
  return {
    site_id: texte(b.site_id) ?? texte(b.id) ?? "",
    code_site: texte(b.code_site) ?? texte(b.site_code) ?? texte(b.code) ?? "—",
    nom_site: texte(b.nom_site) ?? texte(b.name),
    adresse: texte(b.adresse) ?? texte(b.address),
    mode: b.mode === "SOUS_COMPTAGE" ? "SOUS_COMPTAGE" : "SONELGAZ",
    demande_deposee: booleen(b.demande_deposee),
    demande_deposee_le: dateCourte(b.demande_deposee_le),
    etude_effectuee: booleen(b.etude_effectuee),
    etude_effectuee_le: dateCourte(b.etude_effectuee_le),
    devis_paye: booleen(b.devis_paye),
    devis_paye_le: dateCourte(b.devis_paye_le),
    site_raccorde: booleen(b.site_raccorde),
    site_raccorde_le: dateCourte(b.site_raccorde_le),
    sous_comptage_permanent: booleen(b.sous_comptage_permanent),
    provisoire_actif: booleen(b.provisoire_actif),
    provisoire_debut: dateCourte(b.provisoire_debut),
    provisoire_fin: dateCourte(b.provisoire_fin),
    montant_mensuel: nombre(b.montant_mensuel, MONTANT_DEFAUT),
    observation: texte(b.observation),
  };
}

function normaliserPaiement(brut: unknown): Paiement {
  const b = enObjet(brut);
  return {
    id: texte(b.id) ?? "",
    mois: dateCourte(b.mois) ?? "",
    date_paiement: dateCourte(b.date_paiement) ?? "",
    montant: nombre(b.montant, MONTANT_DEFAUT),
    observation: texte(b.observation),
  };
}

async function chargerPaiements(siteId: string): Promise<Paiement[]> {
  const reponse: unknown = await api.get(`${BASE}/${encodeURIComponent(siteId)}/paiements`);
  const donnees = extraire(reponse);
  const liste: unknown[] = Array.isArray(donnees) ? donnees : [];
  return liste
    .map(normaliserPaiement)
    .filter((p) => p.mois !== "")
    .sort((a, b) => (a.mois < b.mois ? 1 : a.mois > b.mois ? -1 : 0));
}

/* ------------------------------------------------------------------ */
/* Dates et montants                                                   */
/* ------------------------------------------------------------------ */

function deuxChiffres(n: number): string {
  return String(n).padStart(2, "0");
}

function aujourdhui(): string {
  const d = new Date();
  return `${d.getFullYear()}-${deuxChiffres(d.getMonth() + 1)}-${deuxChiffres(d.getDate())}`;
}

// "YYYY-MM" du mois en cours
function moisCourantCourt(): string {
  const d = new Date();
  return `${d.getFullYear()}-${deuxChiffres(d.getMonth() + 1)}`;
}

function formaterDate(valeur: string | null): string {
  if (valeur === null || valeur === "") {
    return "—";
  }
  const [annee, mois, jour] = valeur.slice(0, 10).split("-");
  return annee && mois && jour ? `${jour}/${mois}/${annee}` : valeur;
}

function formaterMois(valeur: string): string {
  const [annee, mois] = valeur.slice(0, 7).split("-");
  return annee && mois ? `${mois}/${annee}` : valeur;
}

function formaterDA(montant: number): string {
  return `${montant.toLocaleString("fr-FR")} DA`;
}

function moisDepuis(debut: string | null): number | null {
  if (debut === null) {
    return null;
  }
  const [a, m] = debut.split("-");
  const annee = Number(a);
  const mois = Number(m);
  if (!Number.isFinite(annee) || !Number.isFinite(mois)) {
    return null;
  }
  const maintenant = new Date();
  const ecart = (maintenant.getFullYear() - annee) * 12 + (maintenant.getMonth() + 1 - mois);
  return Math.max(0, ecart);
}

/* ------------------------------------------------------------------ */
/* Règles métier                                                       */
/* ------------------------------------------------------------------ */

function etapeDe(site: SiteEnergie): Etape {
  if (site.site_raccorde) return "RACCORDE";
  if (site.devis_paye) return "DEVIS";
  if (site.etude_effectuee) return "ETUDE";
  if (site.demande_deposee) return "DEMANDE";
  return "NON_DEMARRE";
}

const LIBELLE_ETAPE: Record<Etape, string> = {
  NON_DEMARRE: "Non démarré",
  DEMANDE: "Demande déposée",
  ETUDE: "Étude faite",
  DEVIS: "Devis payé",
  RACCORDE: "Raccordé",
};

function progressionDe(site: SiteEnergie): string {
  if (site.mode === "SOUS_COMPTAGE") {
    return site.sous_comptage_permanent
      ? "Sous-comptage permanent"
      : "Sous-comptage non permanent";
  }
  return LIBELLE_ETAPE[etapeDe(site)];
}

function provisoireEnCours(site: SiteEnergie): boolean {
  return site.provisoire_actif && site.provisoire_fin === null && !site.site_raccorde;
}

function payeCeMois(site: SiteEnergie, paiements: PaiementsParSite): boolean {
  const cle = moisCourantCourt();
  const liste = paiements[site.site_id] ?? [];
  return liste.some((p) => p.mois.slice(0, 7) === cle);
}

function aPayerCeMois(site: SiteEnergie, paiements: PaiementsParSite): boolean {
  return provisoireEnCours(site) && !payeCeMois(site, paiements);
}

interface ResumePaiements {
  nombre: number;
  total: number;
  dernier: string | null;
}

function resumer(liste: Paiement[]): ResumePaiements {
  let total = 0;
  let dernier: string | null = null;
  for (const p of liste) {
    total += p.montant;
    if (dernier === null || p.mois > dernier) {
      dernier = p.mois;
    }
  }
  return { nombre: liste.length, total, dernier };
}

function versFormulaire(site: SiteEnergie): FormulaireSite {
  return {
    mode: site.mode,
    demande_deposee: site.demande_deposee,
    demande_deposee_le: site.demande_deposee_le ?? "",
    etude_effectuee: site.etude_effectuee,
    etude_effectuee_le: site.etude_effectuee_le ?? "",
    devis_paye: site.devis_paye,
    devis_paye_le: site.devis_paye_le ?? "",
    site_raccorde: site.site_raccorde,
    site_raccorde_le: site.site_raccorde_le ?? "",
    sous_comptage_permanent: site.sous_comptage_permanent,
    provisoire_actif: site.provisoire_actif,
    provisoire_debut: site.provisoire_debut ?? "",
    provisoire_fin: site.provisoire_fin ?? "",
    montant_mensuel: String(site.montant_mensuel),
    observation: site.observation ?? "",
  };
}

function videEnNull(valeur: string): string | null {
  return valeur.trim() === "" ? null : valeur;
}

/* ------------------------------------------------------------------ */
/* Styles réutilisés                                                   */
/* ------------------------------------------------------------------ */

const CHAMP =
  "rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm text-mz-text";
const BOUTON_PRINCIPAL =
  "rounded-mz-md bg-mz-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60";
const BOUTON_SECONDAIRE =
  "rounded-mz-md border border-mz-border px-3 py-1.5 text-xs font-medium hover:bg-mz-surface-2";

/* ------------------------------------------------------------------ */
/* Petits composants                                                   */
/* ------------------------------------------------------------------ */

interface PastilleProps {
  ok: boolean;
  libelle: string;
}

function Pastille({ ok, libelle }: PastilleProps) {
  return (
    <span
      className={
        ok
          ? "inline-flex items-center gap-1 text-xs text-emerald-400"
          : "inline-flex items-center gap-1 text-xs text-mz-text-muted"
      }
    >
      <CheckCircle2 size={13} className={ok ? "" : "opacity-30"} />
      {libelle}
    </span>
  );
}

interface LigneEtapeProps {
  libelle: string;
  coche: boolean;
  date: string;
  onCoche: (valeur: boolean) => void;
  onDate: (valeur: string) => void;
}

function LigneEtape({ libelle, coche, date, onCoche, onDate }: LigneEtapeProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex w-48 items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={coche}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onCoche(e.target.checked)}
        />
        {libelle}
      </label>
      <input
        type="date"
        value={date}
        disabled={!coche}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onDate(e.target.value)}
        className={`${CHAMP} disabled:opacity-40`}
        aria-label={`Date : ${libelle}`}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Fiche d'un site (fenêtre de modification + versements)              */
/* ------------------------------------------------------------------ */

interface FicheSiteProps {
  site: SiteEnergie;
  onFermer: () => void;
  onChange: () => Promise<void>;
}

function FicheSite({ site, onFermer, onChange }: FicheSiteProps) {
  const [form, setForm] = useState<FormulaireSite>(() => versFormulaire(site));
  const [paiements, setPaiements] = useState<Paiement[]>([]);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreurFiche, setErreurFiche] = useState<string | null>(null);
  const [infoFiche, setInfoFiche] = useState<string | null>(null);

  const [moisSaisi, setMoisSaisi] = useState(moisCourantCourt());
  const [dateSaisie, setDateSaisie] = useState(aujourdhui());
  const [montantSaisi, setMontantSaisi] = useState(String(site.montant_mensuel));
  const [observationSaisie, setObservationSaisie] = useState("");

  useEffect(() => {
    let actif = true;
    chargerPaiements(site.site_id)
      .then((liste) => {
        if (actif) {
          setPaiements(liste);
        }
      })
      .catch((err: unknown) => {
        if (actif) {
          setErreurFiche(messageErreur(err));
        }
      });
    return () => {
      actif = false;
    };
  }, [site.site_id]);

  function maj<K extends keyof FormulaireSite>(cle: K, valeur: FormulaireSite[K]): void {
    setForm((precedent) => ({ ...precedent, [cle]: valeur }));
  }

  async function enregistrer(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setErreurFiche(null);
    setInfoFiche(null);
    const montant = Number(form.montant_mensuel);
    if (!Number.isFinite(montant) || montant <= 0) {
      setErreurFiche("Le montant mensuel doit être un nombre positif.");
      return;
    }
    setEnregistrement(true);
    try {
      await api.put(`${BASE}/${encodeURIComponent(site.site_id)}`, {
        mode: form.mode,
        demande_deposee: form.demande_deposee,
        demande_deposee_le: form.demande_deposee ? videEnNull(form.demande_deposee_le) : null,
        etude_effectuee: form.etude_effectuee,
        etude_effectuee_le: form.etude_effectuee ? videEnNull(form.etude_effectuee_le) : null,
        devis_paye: form.devis_paye,
        devis_paye_le: form.devis_paye ? videEnNull(form.devis_paye_le) : null,
        site_raccorde: form.site_raccorde,
        site_raccorde_le: form.site_raccorde ? videEnNull(form.site_raccorde_le) : null,
        sous_comptage_permanent: form.sous_comptage_permanent,
        provisoire_actif: form.provisoire_actif,
        provisoire_debut: form.provisoire_actif ? videEnNull(form.provisoire_debut) : null,
        provisoire_fin: form.provisoire_actif ? videEnNull(form.provisoire_fin) : null,
        montant_mensuel: montant,
        observation: videEnNull(form.observation),
      });
      setInfoFiche("Fiche enregistrée.");
      await onChange();
    } catch (err) {
      setErreurFiche(messageErreur(err));
    } finally {
      setEnregistrement(false);
    }
  }

  async function ajouterVersement(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setErreurFiche(null);
    setInfoFiche(null);
    const montant = Number(montantSaisi);
    if (moisSaisi === "" || dateSaisie === "") {
      setErreurFiche("Indiquez le mois concerné et la date de paiement.");
      return;
    }
    if (!Number.isFinite(montant) || montant <= 0) {
      setErreurFiche("Le montant du versement doit être un nombre positif.");
      return;
    }
    setEnregistrement(true);
    try {
      await api.post(`${BASE}/${encodeURIComponent(site.site_id)}/paiements`, {
        mois: `${moisSaisi}-01`,
        date_paiement: dateSaisie,
        montant,
        observation: videEnNull(observationSaisie),
      });
      setObservationSaisie("");
      setInfoFiche(`Versement de ${formaterMois(`${moisSaisi}-01`)} enregistré.`);
      setPaiements(await chargerPaiements(site.site_id));
      await onChange();
    } catch (err) {
      setErreurFiche(messageErreur(err));
    } finally {
      setEnregistrement(false);
    }
  }

  const resume = resumer(paiements);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Fiche énergie ${site.code_site}`}
    >
      <div className="w-full max-w-3xl space-y-5 rounded-mz-md border border-mz-border bg-mz-surface p-5 text-mz-text">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">
              {site.code_site}
              {site.nom_site ? ` — ${site.nom_site}` : ""}
            </h2>
            {site.adresse ? (
              <p className="text-xs text-mz-text-muted">{site.adresse}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onFermer}
            className={BOUTON_SECONDAIRE}
            aria-label="Fermer la fiche"
          >
            <X size={14} />
          </button>
        </div>

        {erreurFiche !== null ? (
          <p className="rounded-mz-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {erreurFiche}
          </p>
        ) : null}
        {infoFiche !== null ? (
          <p className="rounded-mz-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
            {infoFiche}
          </p>
        ) : null}

        <form onSubmit={enregistrer} className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm" htmlFor="mode-alimentation">
              Mode d&apos;alimentation
            </label>
            <select
              id="mode-alimentation"
              value={form.mode}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                maj("mode", e.target.value === "SOUS_COMPTAGE" ? "SOUS_COMPTAGE" : "SONELGAZ")
              }
              className={CHAMP}
            >
              <option value="SONELGAZ">Raccordement Sonelgaz</option>
              <option value="SOUS_COMPTAGE">Sous-comptage</option>
            </select>
          </div>

          {form.mode === "SONELGAZ" ? (
            <div className="space-y-3 rounded-mz-md border border-mz-border p-3">
              <p className="text-sm font-medium">Suivi du raccordement Sonelgaz</p>
              <LigneEtape
                libelle="Demande SNG déposée"
                coche={form.demande_deposee}
                date={form.demande_deposee_le}
                onCoche={(v) => maj("demande_deposee", v)}
                onDate={(v) => maj("demande_deposee_le", v)}
              />
              <LigneEtape
                libelle="Étude effectuée"
                coche={form.etude_effectuee}
                date={form.etude_effectuee_le}
                onCoche={(v) => maj("etude_effectuee", v)}
                onDate={(v) => maj("etude_effectuee_le", v)}
              />
              <LigneEtape
                libelle="Devis payé"
                coche={form.devis_paye}
                date={form.devis_paye_le}
                onCoche={(v) => maj("devis_paye", v)}
                onDate={(v) => maj("devis_paye_le", v)}
              />
              <LigneEtape
                libelle="Site raccordé"
                coche={form.site_raccorde}
                date={form.site_raccorde_le}
                onCoche={(v) => maj("site_raccorde", v)}
                onDate={(v) => maj("site_raccorde_le", v)}
              />
            </div>
          ) : (
            <div className="rounded-mz-md border border-mz-border p-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.sous_comptage_permanent}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    maj("sous_comptage_permanent", e.target.checked)
                  }
                />
                Sous-comptage permanent
              </label>
            </div>
          )}

          {form.mode === "SONELGAZ" ? (
            <div className="space-y-3 rounded-mz-md border border-mz-border p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={form.provisoire_actif}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    maj("provisoire_actif", e.target.checked)
                  }
                />
                Sous-comptage provisoire pendant l&apos;attente Sonelgaz
              </label>
              {form.provisoire_actif ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <label className="text-xs text-mz-text-muted">
                    Début
                    <input
                      type="date"
                      value={form.provisoire_debut}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        maj("provisoire_debut", e.target.value)
                      }
                      className={`${CHAMP} mt-1 w-full`}
                    />
                  </label>
                  <label className="text-xs text-mz-text-muted">
                    Fin
                    <input
                      type="date"
                      value={form.provisoire_fin}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        maj("provisoire_fin", e.target.value)
                      }
                      className={`${CHAMP} mt-1 w-full`}
                    />
                  </label>
                  <label className="text-xs text-mz-text-muted">
                    Montant mensuel (DA)
                    <input
                      type="number"
                      min={0}
                      value={form.montant_mensuel}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        maj("montant_mensuel", e.target.value)
                      }
                      className={`${CHAMP} mt-1 w-full`}
                    />
                  </label>
                </div>
              ) : null}
            </div>
          ) : null}

          <label className="block text-xs text-mz-text-muted">
            Observation
            <textarea
              rows={2}
              value={form.observation}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
                maj("observation", e.target.value)
              }
              className={`${CHAMP} mt-1 w-full`}
            />
          </label>

          <div className="flex justify-end">
            <button type="submit" disabled={enregistrement} className={BOUTON_PRINCIPAL}>
              {enregistrement ? "Enregistrement…" : "Enregistrer la fiche"}
            </button>
          </div>
        </form>

        <div className="space-y-3 border-t border-mz-border pt-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold">Versements mensuels au candidat</h3>
            <p className="text-xs text-mz-text-muted">
              {resume.nombre} versement{resume.nombre > 1 ? "s" : ""} — total{" "}
              {formaterDA(resume.total)}
            </p>
          </div>

          <form
            onSubmit={ajouterVersement}
            className="grid grid-cols-1 gap-3 sm:grid-cols-5"
          >
            <label className="text-xs text-mz-text-muted">
              Mois concerné
              <input
                type="month"
                value={moisSaisi}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setMoisSaisi(e.target.value)}
                className={`${CHAMP} mt-1 w-full`}
              />
            </label>
            <label className="text-xs text-mz-text-muted">
              Date de paiement
              <input
                type="date"
                value={dateSaisie}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDateSaisie(e.target.value)}
                className={`${CHAMP} mt-1 w-full`}
              />
            </label>
            <label className="text-xs text-mz-text-muted">
              Montant (DA)
              <input
                type="number"
                min={0}
                value={montantSaisi}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setMontantSaisi(e.target.value)}
                className={`${CHAMP} mt-1 w-full`}
              />
            </label>
            <label className="text-xs text-mz-text-muted sm:col-span-2">
              Observation
              <input
                value={observationSaisie}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setObservationSaisie(e.target.value)
                }
                className={`${CHAMP} mt-1 w-full`}
              />
            </label>
            <div className="sm:col-span-5">
              <button type="submit" disabled={enregistrement} className={BOUTON_PRINCIPAL}>
                Ajouter le versement
              </button>
            </div>
          </form>

          {paiements.length === 0 ? (
            <p className="text-sm text-mz-text-muted">Aucun versement enregistré pour ce site.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-mz-border text-xs text-mz-text-muted">
                <tr>
                  <th className="py-2">Mois</th>
                  <th className="py-2">Payé le</th>
                  <th className="py-2">Montant</th>
                  <th className="py-2">Observation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-mz-border">
                {paiements.map((p) => (
                  <tr key={p.id !== "" ? p.id : p.mois}>
                    <td className="py-2">{formaterMois(p.mois)}</td>
                    <td className="py-2">{formaterDate(p.date_paiement)}</td>
                    <td className="py-2">{formaterDA(p.montant)}</td>
                    <td className="py-2 text-mz-text-muted">{p.observation ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function EnergiePage() {
  const [sites, setSites] = useState<SiteEnergie[]>([]);
  const [paiementsParSite, setPaiementsParSite] = useState<PaiementsParSite>({});
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const [recherche, setRecherche] = useState("");
  const [filtreMode, setFiltreMode] = useState<"TOUS" | Mode>("TOUS");
  const [filtreEtape, setFiltreEtape] = useState<"TOUTES" | Etape>("TOUTES");
  const [seulementAPayer, setSeulementAPayer] = useState(false);
  const [selection, setSelection] = useState<SiteEnergie | null>(null);

  const charger = useCallback(async (): Promise<void> => {
    setChargement(true);
    setErreur(null);
    try {
      const reponse: unknown = await api.get(BASE);
      const donnees = extraire(reponse);
      const brutes: unknown[] = Array.isArray(donnees) ? donnees : [];
      const liste = brutes.map(normaliserSite).filter((s) => s.site_id !== "");
      setSites(liste);

      const actifs = liste.filter((s) => s.provisoire_actif);
      const resultats = await Promise.all(
        actifs.map(async (s): Promise<[string, Paiement[]]> => {
          try {
            return [s.site_id, await chargerPaiements(s.site_id)];
          } catch {
            return [s.site_id, []];
          }
        }),
      );
      setPaiementsParSite(Object.fromEntries(resultats));
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  async function marquerPaye(site: SiteEnergie): Promise<void> {
    setErreur(null);
    setInfo(null);
    try {
      await api.post(`${BASE}/${encodeURIComponent(site.site_id)}/paiements`, {
        mois: `${moisCourantCourt()}-01`,
        date_paiement: aujourdhui(),
        montant: site.montant_mensuel,
        observation: null,
      });
      setInfo(`Versement du mois enregistré pour ${site.code_site}.`);
      await charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  }

  const compteurs = useMemo(() => {
    const sonelgaz = sites.filter((s) => s.mode === "SONELGAZ");
    const enAttente = sonelgaz.filter((s) => !s.site_raccorde).length;
    const raccordes = sonelgaz.filter((s) => s.site_raccorde).length;
    const provisoires = sites.filter(provisoireEnCours);
    const aPayer = provisoires.filter((s) => aPayerCeMois(s, paiementsParSite));
    const montantAPayer = aPayer.reduce((somme, s) => somme + s.montant_mensuel, 0);
    return {
      total: sites.length,
      enAttente,
      raccordes,
      provisoires: provisoires.length,
      aPayer: aPayer.length,
      montantAPayer,
    };
  }, [sites, paiementsParSite]);

  const sitesFiltres = useMemo(() => {
    const terme = recherche.trim().toLowerCase();
    return sites.filter((s) => {
      if (terme !== "") {
        const cible = `${s.code_site} ${s.nom_site ?? ""}`.toLowerCase();
        if (!cible.includes(terme)) {
          return false;
        }
      }
      if (filtreMode !== "TOUS" && s.mode !== filtreMode) {
        return false;
      }
      if (filtreEtape !== "TOUTES" && (s.mode !== "SONELGAZ" || etapeDe(s) !== filtreEtape)) {
        return false;
      }
      if (seulementAPayer && !aPayerCeMois(s, paiementsParSite)) {
        return false;
      }
      return true;
    });
  }, [sites, paiementsParSite, recherche, filtreMode, filtreEtape, seulementAPayer]);

  return (
    <div className="space-y-6 p-6 text-mz-text">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Zap className="text-mz-primary" size={24} />
          Énergie et raccordement
        </h1>
        <p className="text-sm text-mz-text-muted">
          Suivi Sonelgaz, sous-comptage permanent et versements mensuels du sous-comptage
          provisoire.
        </p>
      </div>

      {erreur !== null ? (
        <p className="rounded-mz-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {erreur}
        </p>
      ) : null}
      {info !== null ? (
        <p className="rounded-mz-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {info}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Sites suivis</p>
          <p className="mt-1 text-2xl font-bold">{compteurs.total}</p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Sonelgaz en attente</p>
          <p className="mt-1 text-2xl font-bold">{compteurs.enAttente}</p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Sites raccordés</p>
          <p className="mt-1 text-2xl font-bold">{compteurs.raccordes}</p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Provisoire en cours</p>
          <p className="mt-1 text-2xl font-bold">{compteurs.provisoires}</p>
        </div>
        <div className="rounded-mz-md border border-amber-500/40 bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">À payer ce mois-ci</p>
          <p className="mt-1 text-2xl font-bold">
            {compteurs.aPayer}{" "}
            <span className="text-sm font-normal text-mz-text-muted">
              ({formaterDA(compteurs.montantAPayer)})
            </span>
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={recherche}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setRecherche(e.target.value)}
          placeholder="Rechercher un code ou un nom de site"
          className={`${CHAMP} w-72`}
          aria-label="Rechercher un site"
        />
        <select
          value={filtreMode}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => {
            const v = e.target.value;
            setFiltreMode(v === "SONELGAZ" || v === "SOUS_COMPTAGE" ? v : "TOUS");
          }}
          className={CHAMP}
          aria-label="Filtrer par mode"
        >
          <option value="TOUS">Tous les modes</option>
          <option value="SONELGAZ">Raccordement Sonelgaz</option>
          <option value="SOUS_COMPTAGE">Sous-comptage</option>
        </select>
        <select
          value={filtreEtape}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => {
            const v = e.target.value;
            const valide: Etape[] = ["NON_DEMARRE", "DEMANDE", "ETUDE", "DEVIS", "RACCORDE"];
            const trouve = valide.find((etape) => etape === v);
            setFiltreEtape(trouve ?? "TOUTES");
          }}
          className={CHAMP}
          aria-label="Filtrer par étape"
        >
          <option value="TOUTES">Toutes les étapes</option>
          <option value="NON_DEMARRE">{LIBELLE_ETAPE.NON_DEMARRE}</option>
          <option value="DEMANDE">{LIBELLE_ETAPE.DEMANDE}</option>
          <option value="ETUDE">{LIBELLE_ETAPE.ETUDE}</option>
          <option value="DEVIS">{LIBELLE_ETAPE.DEVIS}</option>
          <option value="RACCORDE">{LIBELLE_ETAPE.RACCORDE}</option>
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={seulementAPayer}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSeulementAPayer(e.target.checked)}
          />
          À payer ce mois-ci
        </label>
      </div>

      <div className="overflow-x-auto rounded-mz-md border border-mz-border bg-mz-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-mz-border bg-mz-surface-2 text-xs text-mz-text-muted">
            <tr>
              <th className="p-3">Site</th>
              <th className="p-3">Progression</th>
              <th className="p-3">Sous-comptage provisoire</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-mz-border">
            {chargement ? (
              <tr>
                <td colSpan={4} className="p-6 text-center text-mz-text-muted">
                  Chargement…
                </td>
              </tr>
            ) : null}
            {!chargement && sitesFiltres.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-6 text-center text-mz-text-muted">
                  Aucun site ne correspond à ces filtres.
                </td>
              </tr>
            ) : null}
            {sitesFiltres.map((s) => {
              const resume = resumer(paiementsParSite[s.site_id] ?? []);
              const duree = moisDepuis(s.provisoire_debut);
              const enCours = provisoireEnCours(s);
              const aPayer = aPayerCeMois(s, paiementsParSite);
              return (
                <tr key={s.site_id}>
                  <td className="p-3">
                    <div className="font-semibold">{s.code_site}</div>
                    <div className="text-xs text-mz-text-muted">{s.nom_site ?? "—"}</div>
                  </td>
                  <td className="p-3">
                    <div className="mb-1 font-medium">{progressionDe(s)}</div>
                    {s.mode === "SONELGAZ" ? (
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        <Pastille ok={s.demande_deposee} libelle="Demande" />
                        <Pastille ok={s.etude_effectuee} libelle="Étude" />
                        <Pastille ok={s.devis_paye} libelle="Devis" />
                        <Pastille ok={s.site_raccorde} libelle="Raccordé" />
                      </div>
                    ) : null}
                  </td>
                  <td className="p-3 text-xs">
                    {s.provisoire_actif ? (
                      <div className="space-y-0.5">
                        <div className="text-sm">
                          {enCours
                            ? `En cours${duree !== null ? ` depuis ${duree} mois` : ""}`
                            : `Terminé le ${formaterDate(s.provisoire_fin ?? s.site_raccorde_le)}`}
                        </div>
                        <div className="text-mz-text-muted">
                          {resume.nombre} versement{resume.nombre > 1 ? "s" : ""} —{" "}
                          {formaterDA(resume.total)}
                        </div>
                        <div className="text-mz-text-muted">
                          Dernier : {resume.dernier !== null ? formaterMois(resume.dernier) : "—"}
                        </div>
                        {enCours ? (
                          aPayer ? (
                            <span className="inline-block rounded-mz-md bg-amber-500/20 px-2 py-0.5 text-amber-300">
                              À payer ce mois-ci
                            </span>
                          ) : (
                            <span className="inline-block rounded-mz-md bg-emerald-500/20 px-2 py-0.5 text-emerald-300">
                              Payé ce mois-ci
                            </span>
                          )
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-mz-text-muted">—</span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setSelection(s)}
                        className={BOUTON_SECONDAIRE}
                      >
                        Ouvrir la fiche
                      </button>
                      {aPayer ? (
                        <button
                          type="button"
                          onClick={() => {
                            void marquerPaye(s);
                          }}
                          className="rounded-mz-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                        >
                          Marquer payé ce mois
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selection !== null ? (
        <FicheSite
          key={selection.site_id}
          site={selection}
          onFermer={() => setSelection(null)}
          onChange={charger}
        />
      ) : null}
    </div>
  );
}
