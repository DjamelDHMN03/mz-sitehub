import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { Badge } from "@/components/Badge";
import { UserCog, Plus, Check, X } from "lucide-react";

interface UserOut {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role_code: string;
  is_active: boolean;
}

interface NewUserForm {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role_code: string;
}

const ROLES = ["ADMIN", "MANAGER", "ACQUISITION", "LECTURE"];

const ROLE_COLORS: Record<string, string> = {
  ADMIN: "#E5484D",
  MANAGER: "#4C9FE8",
  ACQUISITION: "#E0A438",
  LECTURE: "#6E687A",
};

export default function UsersPage() {
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewUserForm>({
    email: "", first_name: "", last_name: "", password: "", role_code: "ACQUISITION",
  });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .get<UserOut[]>("/users")
      .then(({ data }) => setUsers(data))
      .catch(() => setError("Impossible de charger les utilisateurs. Vérifiez vos permissions."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const toggleActive = async (user: UserOut) => {
    const action = user.is_active ? "désactiver" : "réactiver";
    if (!confirm(`Voulez-vous ${action} le compte de ${user.email} ?`)) return;
    try {
      await api.patch(`/users/${user.id}`, { is_active: !user.is_active });
      load();
    } catch {
      alert("Erreur lors de la modification.");
    }
  };

  const createUser = async () => {
    setFormError(null);
    if (!form.email || !form.password) {
      setFormError("Email et mot de passe sont obligatoires.");
      return;
    }
    if (form.password.length < 8) {
      setFormError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/users", form);
      setShowForm(false);
      setForm({ email: "", first_name: "", last_name: "", password: "", role_code: "ACQUISITION" });
      load();
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || "Erreur lors de la création.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-mz-text">Collaborateurs</h1>
          <p className="text-sm text-mz-text-muted mt-1">
            Gérez les comptes utilisateurs et leurs droits d'accès.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus size={14} /> Nouveau collaborateur
        </Button>
      </div>

      {/* Formulaire de création */}
      {showForm && (
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-4 space-y-3">
          <h2 className="text-sm font-semibold text-mz-text">Nouveau collaborateur</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-mz-text-muted">Prénom</label>
              <input
                className="w-full mt-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                placeholder="Prénom"
              />
            </div>
            <div>
              <label className="text-xs text-mz-text-muted">Nom</label>
              <input
                className="w-full mt-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                placeholder="Nom"
              />
            </div>
            <div>
              <label className="text-xs text-mz-text-muted">Email *</label>
              <input
                className="w-full mt-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="email@exemple.com"
              />
            </div>
            <div>
              <label className="text-xs text-mz-text-muted">Mot de passe * (min. 8 car.)</label>
              <input
                className="w-full mt-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="text-xs text-mz-text-muted">Rôle</label>
              <select
                className="w-full mt-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text"
                value={form.role_code}
                onChange={(e) => setForm({ ...form, role_code: e.target.value })}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>
          {formError && <p className="text-sm text-mz-danger">{formError}</p>}
          <div className="flex gap-2">
            <Button size="sm" onClick={createUser} disabled={saving}>
              {saving ? "Création..." : "Créer le compte"}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setShowForm(false)}>
              Annuler
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-mz-md border border-mz-border bg-mz-surface p-6 text-center">
          <UserCog size={40} className="mx-auto mb-3 text-mz-text-disabled" />
          <p className="text-mz-text-muted text-sm">{error}</p>
          <p className="text-mz-text-disabled text-xs mt-2">
            Cette fonctionnalité est réservée aux administrateurs.
            <br />Le endpoint <code>/users</code> sera disponible après connexion avec un compte ADMIN.
          </p>
        </div>
      )}

      {!loading && !error && users.length === 0 && (
        <p className="text-sm text-mz-text-muted">Aucun utilisateur trouvé.</p>
      )}

      {users.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th>Nom</Th>
              <Th>Email</Th>
              <Th>Rôle</Th>
              <Th>Statut</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <tbody>
            {users.map((user) => (
              <Tr key={user.id}>
                <Td className="font-medium">
                  {user.first_name || user.last_name
                    ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
                    : "—"}
                </Td>
                <Td>{user.email}</Td>
                <Td>
                  <Badge color={ROLE_COLORS[user.role_code] ?? "#6E687A"}>
                    {user.role_code}
                  </Badge>
                </Td>
                <Td>
                  {user.is_active ? (
                    <span className="flex items-center gap-1 text-xs text-mz-success">
                      <Check size={12} /> Actif
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-mz-text-disabled">
                      <X size={12} /> Désactivé
                    </span>
                  )}
                </Td>
                <Td>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => toggleActive(user)}
                  >
                    {user.is_active ? "Désactiver" : "Réactiver"}
                  </Button>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
