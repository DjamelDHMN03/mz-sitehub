import { useEffect, useState } from "react";
import { Zap, FileDown, CheckCircle2 } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface SiteEnergie {
  code_site: string;
  nom_site: string;
  adresse: string;
  longitude: string;
  latitude: string;
  proprietaire: string;
  mode_alimentation: "provisoire" | "sonelgaz";
  loyer_mensuel_da: number;
  mois_payes: number;
  etude_faite: boolean;
  devis_paye: boolean;
  branche: boolean;
  necessite_extension: boolean;
  aps_pret: boolean;
  plan_situation_pret: boolean;
  demande_sonelgaz_prete: boolean;
}

const EMPTY_FORM: SiteEnergie = {
  code_site: "",
  nom_site: "",
  adresse: "",
  longitude: "",
  latitude: "",
  proprietaire: "",
  mode_alimentation: "sonelgaz",
  loyer_mensuel_da: 18000,
  mois_payes: 0,
  etude_faite: false,
  devis_paye: false,
  branche: false,
  necessite_extension: false,
  aps_pret: false,
  plan_situation_pret: false,
  demande_sonelgaz_prete: false,
};

export default function EnergiePage() {
  const [sites, setSites] = useState<SiteEnergie[]>([]);
  const [form, setForm] = useState<SiteEnergie>(EMPTY_FORM);
  const [dateDemande, setDateDemande] = useState("……….");
  const [loading, setLoading] = useState(false);

  async function chargerSites() {
    const res = await fetch(`${API_BASE}/api/energie/sites`);
    if (res.ok) {
      const data = await res.json();
      setSites(data);
    }
  }

  useEffect(() => {
    chargerSites();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/energie/sites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, loyer_mensuel_da: 18000 }),
      });
      if (res.ok) {
        setForm(EMPTY_FORM);
        await chargerSites();
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleGenererDoc(codeSite: string) {
    const url = `${API_BASE}/api/energie/sites/${encodeURIComponent(
      codeSite
    )}/generer-demande?date_demande=${encodeURIComponent(dateDemande)}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) return;
    const blob = await res.blob();
    const dlUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = dlUrl;
    a.download = `Demande_Sonelgaz_${codeSite.replace(/\s+/g, "_")}.docx`;
    a.click();
    window.URL.revokeObjectURL(dlUrl);
    await chargerSites();
  }

  const sitesProvisoires = sites.filter((s) => s.mode_alimentation === "provisoire");
  const chargeMensuelleProv = sitesProvisoires.length * 18000;
  const sitesBranches = sites.filter((s) => s.branche).length;
  const extensionsActives = sites.filter((s) => s.necessite_extension && !s.branche).length;

  return (
    <div className="space-y-6 p-6 text-mz-text">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Zap className="text-mz-primary" size={24} />
            Énergie &amp; Raccordement Sonelgaz
          </h1>
          <p className="text-sm text-mz-text-muted">
            Branchement provisoire (18 000 DA/mois), raccordement Sonelgaz et dossiers d&apos;extension.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-mz-text-muted">Date après &laquo; Alger, le &raquo; :</label>
          <input
            value={dateDemande}
            onChange={(e) => setDateDemande(e.target.value)}
            className="rounded-mz-md border border-mz-border bg-mz-surface px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Sites suivis</p>
          <p className="mt-1 text-2xl font-bold">{sites.length}</p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Provisoire (18 000 DA/mois)</p>
          <p className="mt-1 text-2xl font-bold">
            {sitesProvisoires.length}{" "}
            <span className="text-sm font-normal text-mz-text-muted">
              ({chargeMensuelleProv.toLocaleString("fr-FR")} DA/mois)
            </span>
          </p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Branchés Sonelgaz</p>
          <p className="mt-1 text-2xl font-bold">{sitesBranches}</p>
        </div>
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4">
          <p className="text-xs text-mz-text-muted">Extensions en cours</p>
          <p className="mt-1 text-2xl font-bold">{extensionsActives}</p>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 gap-3 rounded-mz-md border border-mz-border bg-mz-surface p-4 md:grid-cols-3"
      >
        <input
          required
          placeholder="Code site (ex: AL2238 A)"
          value={form.code_site}
          onChange={(e) => setForm({ ...form, code_site: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Nom du site (ex: KOURIFFA)"
          value={form.nom_site}
          onChange={(e) => setForm({ ...form, nom_site: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Propriétaire (ex: Domaines)"
          value={form.proprietaire}
          onChange={(e) => setForm({ ...form, proprietaire: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Adresse complète"
          value={form.adresse}
          onChange={(e) => setForm({ ...form, adresse: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm md:col-span-2"
        />
        <select
          value={form.mode_alimentation}
          onChange={(e) =>
            setForm({
              ...form,
              mode_alimentation: e.target.value as "provisoire" | "sonelgaz",
            })
          }
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        >
          <option value="sonelgaz">Raccordement Sonelgaz</option>
          <option value="provisoire">Branchement provisoire (18 000 DA/mois)</option>
        </select>
        <input
          required
          placeholder="Longitude (ex: 3.141391)"
          value={form.longitude}
          onChange={(e) => setForm({ ...form, longitude: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Latitude (ex: 36.704134)"
          value={form.latitude}
          onChange={(e) => setForm({ ...form, latitude: e.target.value })}
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />
        <input
          type="number"
          min={0}
          placeholder="Mois provisoires payés"
          value={form.mois_payes}
          onChange={(e) =>
            setForm({ ...form, mois_payes: parseInt(e.target.value || "0", 10) })
          }
          className="rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2 text-sm"
        />

        <div className="flex flex-wrap items-center gap-4 text-sm md:col-span-3">
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.etude_faite}
              onChange={(e) => setForm({ ...form, etude_faite: e.target.checked })}
            />
            Étude faite
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.devis_paye}
              onChange={(e) => setForm({ ...form, devis_paye: e.target.checked })}
            />
            Devis payé
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.branche}
              onChange={(e) => setForm({ ...form, branche: e.target.checked })}
            />
            Branché
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.necessite_extension}
              onChange={(e) =>
                setForm({ ...form, necessite_extension: e.target.checked })
              }
            />
            Nécessite extension
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.aps_pret}
              onChange={(e) => setForm({ ...form, aps_pret: e.target.checked })}
            />
            APS prêt
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.plan_situation_pret}
              onChange={(e) =>
                setForm({ ...form, plan_situation_pret: e.target.checked })
              }
            />
            Plan de situation prêt
          </label>
          <button
            type="submit"
            disabled={loading}
            className="ml-auto rounded-mz-md bg-mz-primary px-4 py-2 text-sm font-medium text-white"
          >
            {loading ? "Enregistrement..." : "Enregistrer / Mettre à jour"}
          </button>
        </div>
      </form>

      <div className="overflow-x-auto rounded-mz-md border border-mz-border bg-mz-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-mz-border bg-mz-surface-2 text-xs text-mz-text-muted">
            <tr>
              <th className="p-3">Site</th>
              <th className="p-3">Alimentation</th>
              <th className="p-3">Sonelgaz</th>
              <th className="p-3">Extension (APS / Plan / Demande)</th>
              <th className="p-3">Document</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-mz-border">
            {sites.map((s) => (
              <tr key={s.code_site}>
                <td className="p-3">
                  <div className="font-semibold">
                    {s.code_site} — {s.nom_site}
                  </div>
                  <div className="text-xs text-mz-text-muted">{s.adresse}</div>
                </td>
                <td className="p-3">
                  {s.mode_alimentation === "provisoire" ? (
                    <div>
                      <span className="font-medium text-amber-400">Provisoire</span> — 18 000 DA/mois
                      <div className="text-xs text-mz-text-muted">
                        {s.mois_payes} mois payés ({(s.mois_payes * 18000).toLocaleString("fr-FR")} DA)
                      </div>
                    </div>
                  ) : (
                    <span>Raccordement Sonelgaz ({s.proprietaire})</span>
                  )}
                </td>
                <td className="p-3">
                  {s.branche ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400">
                      <CheckCircle2 size={15} /> Branché
                    </span>
                  ) : (
                    <div className="space-y-0.5 text-xs">
                      <div>Étude faite : {s.etude_faite ? "Oui" : "Non"}</div>
                      <div>Devis payé : {s.devis_paye ? "Oui" : "Non"}</div>
                    </div>
                  )}
                </td>
                <td className="p-3 text-xs">
                  {!s.necessite_extension ? (
                    <span className="text-mz-text-muted">Non requise</span>
                  ) : (
                    <div className="space-y-0.5">
                      <div>APS : {s.aps_pret ? "Prêt" : "Manquant"}</div>
                      <div>Plan de situation : {s.plan_situation_pret ? "Prêt" : "Manquant"}</div>
                      <div>Demande Sonelgaz : {s.demande_sonelgaz_prete ? "Prête" : "À générer"}</div>
                    </div>
                  )}
                </td>
                <td className="p-3">
                  <button
                    type="button"
                    onClick={() => handleGenererDoc(s.code_site)}
                    className="inline-flex items-center gap-1.5 rounded-mz-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                  >
                    <FileDown size={14} /> Demande (.docx)
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
