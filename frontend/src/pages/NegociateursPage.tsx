import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";

interface NegociateurStats {
  user_id: string | null;
  full_name: string;
  contrats_signes: number;
  assignes: number;
  en_cours: number;
  negociation: number;
  valides: number;
  bloques: number;
}

const REFRESH_MS = 60000;
const INPUT_CLASS =
  "mt-1 w-full rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary";

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : "Une erreur est survenue. R\u00e9essayez.";
}

export default function NegociateursPage() {
  const [rows, setRows] = useState<NegociateurStats[] | null>(null);
  const [error, setError] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .get<NegociateurStats[]>("/stats/negociateurs")
      .then(({ data }) => {
        setRows(data);
        setError(false);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    window.addEventListener("mz:sites-changed", load);
    return () => {
      clearInterval(timer);
      window.removeEventListener("mz:sites-changed", load);
    };
  }, [load]);

  async function addFreelance(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!firstName.trim() && !lastName.trim()) {
      setFormError("Indiquez au moins un nom ou un pr\u00e9nom.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/users/freelance", {
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
      });
      setFirstName("");
      setLastName("");
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-mz-text-muted">
        {"Sites assign\u00e9s par n\u00e9gociateur (hors corbeille). Cliquez sur un nom pour voir ses sites."}
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          {"+ Ajouter un n\u00e9gociateur"}
        </Button>
        <Link to="/utilisateurs" className="text-xs text-mz-text-muted underline">
          {"Cr\u00e9er un compte avec connexion"}
        </Link>
      </div>

      {showForm && (
        <form
          onSubmit={addFreelance}
          className="space-y-3 rounded-mz-md border border-mz-border bg-mz-surface p-4"
        >
          <p className="text-sm font-semibold text-mz-text">{"Nouveau n\u00e9gociateur (freelance)"}</p>
          <p className="text-xs text-mz-text-muted">
            {"Sans adresse e-mail ni mot de passe : il ne se connecte pas \u00e0 l\u2019application. Ses sites sont g\u00e9r\u00e9s par un administrateur ou un manager."}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="nego-first" className="text-xs text-mz-text-muted">
                {"Pr\u00e9nom"}
              </label>
              <input
                id="nego-first"
                className={INPUT_CLASS}
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="nego-last" className="text-xs text-mz-text-muted">
                Nom
              </label>
              <input
                id="nego-last"
                className={INPUT_CLASS}
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-mz-danger">{formError}</p>}
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? "Enregistrement..." : "Ajouter"}
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => setShowForm(false)}>
              Annuler
            </Button>
          </div>
        </form>
      )}

      {error && <p className="text-sm text-mz-danger">Statistiques indisponibles.</p>}
      {!error && rows === null && <p className="text-sm text-mz-text-muted">Chargement...</p>}
      {rows && rows.length === 0 && (
        <p className="text-sm text-mz-text-muted">{"Aucun n\u00e9gociateur."}</p>
      )}
      {rows && rows.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th>{"N\u00e9gociateur"}</Th>
              <Th>{"Contrats sign\u00e9s"}</Th>
              <Th>{"Assign\u00e9s"}</Th>
              <Th>En cours</Th>
              <Th>{"N\u00e9gociation"}</Th>
              <Th>{"Valid\u00e9s"}</Th>
              <Th>{"Bloqu\u00e9s"}</Th>
            </Tr>
          </Thead>
          <tbody>
            {rows.map((r) => (
              <Tr key={r.user_id ?? "none"}>
                <Td className="font-medium">
                  {r.user_id ? (
                    <Link to={`/sites?responsable=${r.user_id}`} className="text-mz-primary hover:underline">
                      {r.full_name}
                    </Link>
                  ) : (
                    r.full_name
                  )}
                </Td>
                <Td className="text-base font-bold text-mz-primary">{r.contrats_signes}</Td>
                <Td>{r.assignes}</Td>
                <Td>{r.en_cours}</Td>
                <Td>{r.negociation}</Td>
                <Td>{r.valides}</Td>
                <Td className={r.bloques > 0 ? "font-semibold text-mz-danger" : ""}>{r.bloques}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}