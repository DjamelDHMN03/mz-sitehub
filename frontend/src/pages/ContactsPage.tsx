import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Plus, Phone, MessageCircle, Mail } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface Contact {
  id: string;
  site_id: string;
  first_name: string | null;
  last_name: string | null;
  role_label: string | null;
  organisme: string | null;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  last_contact_at: string | null;
  next_followup_at: string | null;
}

interface Interaction {
  id: string;
  interaction_type: string;
  summary: string | null;
  result: string | null;
  next_action: string | null;
  followup_at: string | null;
  created_at: string;
}

interface ContactRole {
  id: number;
  code: string;
  label: string;
}

const INTERACTION_ICONS: Record<string, typeof Phone> = {
  APPEL: Phone,
  WHATSAPP: MessageCircle,
  EMAIL: Mail,
};

export default function ContactsPage() {
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState<string>("");
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [roles, setRoles] = useState<ContactRole[]>([]);
  const [selectedContactId, setSelectedContactId] = useState<string | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [showNewContact, setShowNewContact] = useState(false);
  const [showNewInteraction, setShowNewInteraction] = useState(false);

  useEffect(() => {
    api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }).then(({ data }) => setSites(data));
    api.get<ContactRole[]>("/contact-roles").then(({ data }) => setRoles(data));
  }, []);

  useEffect(() => {
    if (!selectedSiteId) {
      setContacts([]);
      return;
    }
    api.get<Contact[]>(`/sites/${selectedSiteId}/contacts`).then(({ data }) => setContacts(data));
    setSelectedContactId(null);
  }, [selectedSiteId]);

  useEffect(() => {
    if (!selectedContactId) {
      setInteractions([]);
      return;
    }
    api.get<Interaction[]>(`/contacts/${selectedContactId}/interactions`).then(({ data }) => setInteractions(data));
  }, [selectedContactId]);

  async function handleCreateContact(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());
    await api.post(`/sites/${selectedSiteId}/contacts`, payload);
    const { data } = await api.get<Contact[]>(`/sites/${selectedSiteId}/contacts`);
    setContacts(data);
    setShowNewContact(false);
  }

  async function handleCreateInteraction(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedContactId) return;
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(form.entries());
    await api.post(`/contacts/${selectedContactId}/interactions`, payload);
    const { data } = await api.get<Interaction[]>(`/contacts/${selectedContactId}/interactions`);
    setInteractions(data);
    setShowNewInteraction(false);
    // Rafraîchit la fiche contact (last_contact_at / next_followup_at mis à jour côté backend)
    const { data: refreshed } = await api.get<Contact[]>(`/sites/${selectedSiteId}/contacts`);
    setContacts(refreshed);
  }

  const selectedContact = contacts.find((c) => c.id === selectedContactId) ?? null;

  return (
    <div className="grid grid-cols-3 gap-4">
      <Card className="col-span-1">
        <CardHeader>
          <CardTitle>Site</CardTitle>
        </CardHeader>
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="w-full rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm text-mz-text"
        >
          <option value="">— Choisir un site —</option>
          {sites?.items.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} {s.name ? `— ${s.name}` : ""}
            </option>
          ))}
        </select>

        {selectedSiteId && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-mz-text-muted">Contacts</p>
              <Button size="sm" variant="ghost" onClick={() => setShowNewContact(!showNewContact)}>
                <Plus size={14} />
              </Button>
            </div>

            {showNewContact && (
              <form onSubmit={handleCreateContact} className="space-y-1.5 rounded-mz-md border border-mz-border p-2">
                <input name="first_name" placeholder="Prénom" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="last_name" placeholder="Nom" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <select name="role_label" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs">
                  <option value="">Fonction...</option>
                  {roles.map((r) => (
                    <option key={r.id} value={r.label}>{r.label}</option>
                  ))}
                </select>
                <input name="phone" placeholder="Téléphone" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <input name="email" placeholder="Email" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-xs" />
                <Button type="submit" size="sm" className="w-full text-xs">Ajouter</Button>
              </form>
            )}

            <ul className="space-y-1">
              {contacts.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => setSelectedContactId(c.id)}
                    className={`w-full rounded-mz-md px-2 py-1.5 text-left text-sm transition-colors ${
                      selectedContactId === c.id ? "bg-mz-primary/15 text-mz-primary" : "hover:bg-mz-surface-2 text-mz-text"
                    }`}
                  >
                    <p className="font-medium">{c.first_name} {c.last_name}</p>
                    {c.role_label && <p className="text-xs text-mz-text-muted">{c.role_label}</p>}
                  </button>
                </li>
              ))}
              {contacts.length === 0 && <p className="text-xs text-mz-text-muted">Aucun contact pour ce site.</p>}
            </ul>
          </div>
        )}
      </Card>

      <Card className="col-span-2">
        {!selectedContact ? (
          <p className="text-sm text-mz-text-muted">Sélectionnez un contact pour voir sa fiche et son historique.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <CardHeader>
                <CardTitle>{selectedContact.first_name} {selectedContact.last_name}</CardTitle>
              </CardHeader>
              <div className="flex flex-wrap gap-2 text-sm">
                {selectedContact.role_label && <Badge tone="info">{selectedContact.role_label}</Badge>}
                {selectedContact.organisme && <Badge>{selectedContact.organisme}</Badge>}
              </div>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-mz-text-muted">
                <p>📞 {selectedContact.phone ?? "À COMPLÉTER"}</p>
                <p>💬 {selectedContact.whatsapp ?? "À COMPLÉTER"}</p>
                <p>✉️ {selectedContact.email ?? "À COMPLÉTER"}</p>
                <p>🔁 Prochaine relance : {selectedContact.next_followup_at ?? "—"}</p>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-mz-text-muted">Historique</p>
                <Button size="sm" variant="secondary" onClick={() => setShowNewInteraction(!showNewInteraction)}>
                  <Plus size={13} /> Nouvelle interaction
                </Button>
              </div>

              {showNewInteraction && (
                <form onSubmit={handleCreateInteraction} className="mb-3 space-y-1.5 rounded-mz-md border border-mz-border p-3">
                  <select name="interaction_type" required className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                    <option value="APPEL">Appel</option>
                    <option value="WHATSAPP">WhatsApp</option>
                    <option value="EMAIL">Email</option>
                    <option value="REUNION">Réunion</option>
                    <option value="VISITE">Visite</option>
                    <option value="COURRIER">Courrier</option>
                    <option value="AUTRE">Autre</option>
                  </select>
                  <textarea name="summary" placeholder="Résumé..." className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" rows={2} />
                  <input name="next_action" placeholder="Prochaine action" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                  <input name="followup_at" type="date" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
                  <Button type="submit" size="sm">Enregistrer</Button>
                </form>
              )}

              <ul className="space-y-2">
                {interactions.map((i) => {
                  const Icon = INTERACTION_ICONS[i.interaction_type] ?? MessageCircle;
                  return (
                    <li key={i.id} className="rounded-mz-md border border-mz-border p-2.5">
                      <div className="mb-1 flex items-center gap-2 text-xs text-mz-text-muted">
                        <Icon size={13} /> {i.interaction_type} · {new Date(i.created_at).toLocaleDateString("fr-FR")}
                      </div>
                      {i.summary && <p className="text-sm text-mz-text">{i.summary}</p>}
                      {i.next_action && <p className="text-xs text-mz-info">Prochaine action : {i.next_action}</p>}
                    </li>
                  );
                })}
                {interactions.length === 0 && <p className="text-sm text-mz-text-muted">Aucune interaction enregistrée.</p>}
              </ul>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
