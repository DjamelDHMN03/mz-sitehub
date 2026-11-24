import { useEffect, useMemo, useState } from "react";
import { Zap, Search, Save, PlusCircle, CheckCircle2, Clock } from "lucide-react";
import { api } from "@/lib/api";

type ModeEnergie = "SONELGAZ" | "SOUS_COMPTAGE";

interface SiteEnergie {
  site_id: string;
  code_site: string;
  nom_site: string;
  adresse: string | null;
  proprietaire: string | null;
  longitude: number | string | null;
  latitude: number | string | null;
  mode: ModeEnergie;
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
  montant_mensuel: number | null;
  necessite_extension: boolean;
  aps_pret: boolean;
  plan_situation_pret: boolean;
  demande_sonelgaz_prete: boolean;
  observation: string | null;
}

interface PaiementEnergie {
  id: string;
  site_id: string;
  mois: string;
  date_paiement: string;
  montant: number;
  observation: string | null;
  created_at?: string;
}

function toDateInput(val: string | null | undefined): string {
  if (!val) return "";
  return val.slice(0, 10);
}

function normalizeMois(val: string): string {
  if (!val) return "";
  return val.length === 7 ? `${val}-01` : val.slice(0, 10);
}

export default function EnergiePage() {
  const [sites, setSites] = useState<SiteEnergie[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [form, setForm] = useState<SiteEnergie | null>(null);
  const [search, setSearch] = useState<string>("");
  const [paiements, setPaiements] = useState<PaiementEnergie[]>([]);

  const [mois, setMois] = useState<string>("2026-11-01");
  const [datePaiement, setDatePaiement] = useState<string>("2026-11-24");
  const [montant, setMontant] = useState<string>("18000");
  const [obsPaiement, setObsPaiement] = useState<string>("");

  const [loadingSites, setLoadingSites] = useState<boolean>(false);
  const [savingSite, setSavingSite] = useState<boolean>(false);
  const [savingPaiement, setSavingPaiement] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  async function chargerSites(keepSiteId?: string) {
    setLoadingSites(true);
    setErrorMsg("");
    try {
      const { data } = await api.get<SiteEnergie[]>("/api/energie/sites");
      setSites(data);
      const targetId = keepSiteId || selectedId || data[0]?.site_id || "";
      if (targetId) {
        const found = data.find((s: SiteEnergie) => s.site_id === targetId) || data[0];
        if (found) {
          setSelectedId(found.site_id);
          setForm({ ...found });
        }
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Erreur chargement des sites énergie.");
    } finally {
      setLoadingSites(false);
    }
  }

  async function chargerPaiements(siteId: string) {
    if (!siteId) return;
    try {
      const { data } = await api.get<PaiementEnergie[]>(
        `/api/energie/sites/${encodeURIComponent(siteId)}/paiements`
      );
      setPaiements(data);
    } catch {
      setPaiements([]);
    }
  }

  useEffect(() => {
    chargerSites();
  }, []);

  useEffect(() => {
    if (selectedId) {
      const found = sites.find((s) => s.site_id === selectedId);
      if (found) setForm({ ...found });
      chargerPaiements(selectedId);
    }
  }, [selectedId]);

  const filteredSites = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return sites;
    return sites.filter(
      (s) =>
        (s.code_site || "").toLowerCase().includes(q) ||
        (s.nom_site || "").toLowerCase().includes(q) ||
        (s.adresse || "").toLowerCase().includes(q)
    );
  }, [sites, search]);

  const stats = useMemo(() => {
    const provisoires = sites.filter((s) => s.provisoire_actif).length;
    const raccordes = sites.filter((s) => s.site_raccorde).length;
    const extensions = sites.filter((s) => s.necessite_extension && !s.site_raccorde).length;
    const chargeMensuelle = sites.reduce((acc, s) => acc + (Number(s.montant_mensuel) || 0), 0);
    return { provisoires, raccordes, extensions, chargeMensuelle };
  }, [sites]);

  async function handleSaveSite(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSavingSite(true);
    setStatusMsg("");
    setErrorMsg("");
    try {
      const payload = {
        mode: form.mode,
        demande_deposee: Boolean(form.demande_deposee),
        demande_deposee_le: toDateInput(form.demande_deposee_le) || null,
        etude_effectuee: Boolean(form.etude_effectuee),
        etude_effectuee_le: toDateInput(form.etude_effectuee_le) || null,
        devis_paye: Boolean(form.devis_paye),
        devis_paye_le: toDateInput(form.devis_paye_le) || null,
        site_raccorde: Boolean(form.site_raccorde),
        site_raccorde_le: toDateInput(form.site_raccorde_le) || null,
        sous_comptage_permanent: Boolean(form.sous_comptage_permanent),
        provisoire_actif: Boolean(form.provisoire_actif),
        provisoire_debut: toDateInput(form.provisoire_debut) || null,
        provisoire_fin: toDateInput(form.provisoire_fin) || null,
        montant_mensuel: form.montant_mensuel === null ? null : Number(form.montant_mensuel),
        necessite_extension: Boolean(form.necessite_extension),
        aps_pret: Boolean(form.aps_pret),
