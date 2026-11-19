import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/Button";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { Globe, Pencil, Trash2, Plus, Check, X } from "lucide-react";

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

const INPUT_CLASS =
  "w-full rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary";

function messageErreur(e: unknown): string {
  const err = e as { response?: { status?: number; data?: { detail?: unknown } } };
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (err.response?.status === 403) return "Vous n'avez pas le droit d'effectuer cette action.";
  return "Une erreur est survenue. Vérifiez que le serveur est joignable.";
}

function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="mb-3 rounded-mz-md border border-mz-danger/40 bg-mz-danger/10 px-3 py-2 text-sm text-mz-danger">
      {message}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Wilayas
// ---------------------------------------------------------------------------
function WilayasPanel({ canEdit }: { canEdit: boolean }) {
  const [items, setItems] = useState<Wilaya[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Wilaya[]>("/geography/wilayas");
      setItems(data);
      setError(null);
    } catch (e) {
      setError(messageErreur(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/geography/wilayas", { id: Number(newId), name: newName.trim() });
      setNewId("");
      setNewName("");
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  async function handleSave(id: number) {
    setError(null);
    try {
      await api.patch(`/geography/wilayas/${id}`, { name: editName.trim() });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  async function handleDelete(w: Wilaya) {
    if (!window.confirm(`Supprimer la wilaya ${String(w.id).padStart(2, "0")} - ${w.name} ?`)) return;
    setError(null);
    try {
      await api.delete(`/geography/wilayas/${w.id}`);
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  return (
    <div>
      <ErrorBanner message={error} />

      {canEdit && (
        <form onSubmit={handleAdd} className="mb-4 flex flex-wrap items-end gap-3">
          <div className="w-28">
            <label className="mb-1 block text-xs font-medium text-mz-text-muted">Code (1 à 99)</label>
            <input
              type="number"
              min={1}
              max={99}
              required
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div className="min-w-[14rem] flex-1">
            <label className="mb-1 block text-xs font-medium text-mz-text-muted">Nom de la wilaya</label>
            <input
              type="text"
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <Button type="submit">
            <Plus size={16} /> Ajouter
          </Button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-mz-text-muted">Chargement...</p>
      ) : items.length === 0 ? (
        <p className="rounded-mz-md border border-dashed border-mz-border px-4 py-6 text-center text-sm text-mz-text-muted">
          Aucune wilaya enregistrée pour le moment.
          {canEdit
            ? " Ajoutez-les avec le formulaire ci-dessus : elles apparaîtront ensuite dans les formulaires de sites."
            : " Un administrateur doit les ajouter."}{" "}
          L'application fonctionne normalement sans elles.
        </p>
      ) : (
        <Table>
          <Thead>
            <tr>
              <Th className="w-24">Code</Th>
              <Th>Nom</Th>
              {canEdit && <Th className="w-32 text-right">Actions</Th>}
            </tr>
          </Thead>
          <tbody>
            {items.map((w) => (
              <Tr key={w.id}>
                <Td>{String(w.id).padStart(2, "0")}</Td>
                <Td>
                  {editingId === w.id ? (
                    <input
                      autoFocus
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className={INPUT_CLASS}
                    />
                  ) : (
                    w.name
                  )}
                </Td>
                {canEdit && (
                  <Td className="text-right">
                    {editingId === w.id ? (
                      <span className="inline-flex gap-1">
                        <Button size="sm" variant="secondary" title="Enregistrer" onClick={() => void handleSave(w.id)}>
                          <Check size={14} />
                        </Button>
                        <Button size="sm" variant="ghost" title="Annuler" onClick={() => setEditingId(null)}>
                          <X size={14} />
                        </Button>
                      </span>
                    ) : (
                      <span className="inline-flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Modifier"
                          onClick={() => {
                            setEditingId(w.id);
                            setEditName(w.name);
                          }}
                        >
                          <Pencil size={14} />
                        </Button>
                        <Button size="sm" variant="ghost" title="Supprimer" onClick={() => void handleDelete(w)}>
                          <Trash2 size={14} />
                        </Button>
                      </span>
                    )}
                  </Td>
                )}
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Communes
// ---------------------------------------------------------------------------
function CommunesPanel({ canEdit }: { canEdit: boolean }) {
  const [wilayas, setWilayas] = useState<Wilaya[]>([]);
  const [items, setItems] = useState<Commune[]>([]);
  const [filterWilaya, setFilterWilaya] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newDaira, setNewDaira] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDaira, setEditDaira] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [w, c] = await Promise.all([
        api.get<Wilaya[]>("/geography/wilayas"),
        api.get<Commune[]>("/geography/communes", {
          params: filterWilaya ? { wilaya_id: Number(filterWilaya) } : undefined,
        }),
      ]);
      setWilayas(w.data);
      setItems(c.data);
      setError(null);
    } catch (e) {
      setError(messageErreur(e));
    } finally {
      setLoading(false);
    }
  }, [filterWilaya]);

  useEffect(() => {
    void load();
  }, [load]);

  function nomWilaya(id: number): string {
    const w = wilayas.find((x) => x.id === id);
    return w ? `${String(w.id).padStart(2, "0")} - ${w.name}` : String(id);
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!filterWilaya) {
      setError("Choisissez d'abord une wilaya dans la liste ci-dessus pour y ajouter une commune.");
      return;
    }
    setError(null);
    try {
      await api.post("/geography/communes", {
        wilaya_id: Number(filterWilaya),
        name: newName.trim(),
        daira: newDaira.trim() || null,
      });
      setNewName("");
      setNewDaira("");
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  async function handleSave(id: number) {
    setError(null);
    try {
      await api.patch(`/geography/communes/${id}`, {
        name: editName.trim(),
        daira: editDaira.trim() || null,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  async function handleDelete(c: Commune) {
    if (!window.confirm(`Supprimer la commune ${c.name} ?`)) return;
    setError(null);
    try {
      await api.delete(`/geography/communes/${c.id}`);
      await load();
    } catch (err) {
      setError(messageErreur(err));
    }
  }

  return (
    <div>
      <ErrorBanner message={error} />

      <div className="mb-4 max-w-sm">
        <label className="mb-1 block text-xs font-medium text-mz-text-muted">Wilaya</label>
        <select value={filterWilaya} onChange={(e) => setFilterWilaya(e.target.value)} className={INPUT_CLASS}>
          <option value="">Toutes les wilayas</option>
          {wilayas.map((w) => (
            <option key={w.id} value={w.id}>
              {String(w.id).padStart(2, "0")} - {w.name}
            </option>
          ))}
        </select>
      </div>

      {canEdit && (
        <form onSubmit={handleAdd} className="mb-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[12rem] flex-1">
            <label className="mb-1 block text-xs font-medium text-mz-text-muted">Nom de la commune</label>
            <input type="text" required value={newName} onChange={(e) => setNewName(e.target.value)} className={INPUT_CLASS} />
          </div>
          <div className="min-w-[12rem] flex-1">
            <label className="mb-1 block text-xs font-medium text-mz-text-muted">Daïra (facultatif)</label>
            <input type="text" value={newDaira} onChange={(e) => setNewDaira(e.target.value)} className={INPUT_CLASS} />
          </div>
          <Button type="submit">
            <Plus size={16} /> Ajouter
          </Button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-mz-text-muted">Chargement...</p>
      ) : items.length === 0 ? (
        <p className="rounded-mz-md border border-dashed border-mz-border px-4 py-6 text-center text-sm text-mz-text-muted">
          {wilayas.length === 0
            ? "Ajoutez d'abord des wilayas (onglet Wilayas) : chaque commune est rattachée à une wilaya."
            : "Aucune commune enregistrée pour cette sélection."}{" "}
          L'application fonctionne normalement sans elles.
        </p>
      ) : (
        <Table>
          <Thead>
            <tr>
              <Th>Commune</Th>
              <Th>Daïra</Th>
              <Th>Wilaya</Th>
              {canEdit && <Th className="w-32 text-right">Actions</Th>}
            </tr>
          </Thead>
          <tbody>
            {items.map((c) => (
              <Tr key={c.id}>
                <Td>
                  {editingId === c.id ? (
                    <input autoFocus value={editName} onChange={(e) => setEditName(e.target.value)} className={INPUT_CLASS} />
                  ) : (
                    c.name
                  )}
                </Td>
                <Td>
                  {editingId === c.id ? (
                    <input value={editDaira} onChange={(e) => setEditDaira(e.target.value)} className={INPUT_CLASS} />
                  ) : (
                    c.daira ?? "—"
                  )}
                </Td>
                <Td>{nomWilaya(c.wilaya_id)}</Td>
                {canEdit && (
                  <Td className="text-right">
                    {editingId === c.id ? (
                      <span className="inline-flex gap-1">
                        <Button size="sm" variant="secondary" title="Enregistrer" onClick={() => void handleSave(c.id)}>
                          <Check size={14} />
                        </Button>
                        <Button size="sm" variant="ghost" title="Annuler" onClick={() => setEditingId(null)}>
                          <X size={14} />
                        </Button>
                      </span>
                    ) : (
                      <span className="inline-flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Modifier"
                          onClick={() => {
                            setEditingId(c.id);
                            setEditName(c.name);
                            setEditDaira(c.daira ?? "");
                          }}
                        >
                          <Pencil size={14} />
                        </Button>
                        <Button size="sm" variant="ghost" title="Supprimer" onClick={() => void handleDelete(c)}>
                          <Trash2 size={14} />
                        </Button>
                      </span>
                    )}
                  </Td>
                )}
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page Paramètres
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"wilayas" | "communes">("wilayas");
  const canEdit = user?.role_code === "ADMIN";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe size={16} /> Données géographiques
          </CardTitle>
        </CardHeader>

        {!canEdit && (
          <p className="mb-3 text-sm text-mz-text-muted">
            Consultation seulement : seul un administrateur peut modifier ces listes.
          </p>
        )}

        <div className="mb-4 flex gap-2 border-b border-mz-border">
          {(["wilayas", "communes"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={
                tab === t
                  ? "border-b-2 border-mz-primary px-3 py-2 text-sm font-medium text-mz-primary"
                  : "px-3 py-2 text-sm text-mz-text-muted hover:text-mz-text"
              }
            >
              {t === "wilayas" ? "Wilayas" : "Communes"}
            </button>
          ))}
        </div>

        {tab === "wilayas" ? <WilayasPanel canEdit={canEdit} /> : <CommunesPanel canEdit={canEdit} />}
      </Card>
    </div>
  );
}
