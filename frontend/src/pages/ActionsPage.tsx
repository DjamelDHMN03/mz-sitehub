import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { Plus, Check } from "lucide-react";

interface TaskOut {
  id: string;
  site_id: string | null;
  title: string;
  priority: number;
  due_date: string | null;
  status: string;
  comment: string | null;
}

const STATUS_LABELS: Record<string, { label: string; tone: "neutral" | "info" | "success" | "danger" }> = {
  A_FAIRE: { label: "À faire", tone: "neutral" },
  EN_COURS: { label: "En cours", tone: "info" },
  TERMINE: { label: "Terminé", tone: "success" },
  ANNULE: { label: "Annulé", tone: "danger" },
};

export default function ActionsPage() {
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  async function refresh() {
    const { data } = await api.get<{ items: TaskOut[]; total: number }>("/tasks", {
      params: { ...(statusFilter ? { status_filter: statusFilter } : {}), page_size: 200 },
    });
    setTasks(data.items);
  }

  useEffect(() => {
    refresh();
  }, [statusFilter]);

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload = Object.fromEntries(Array.from(form.entries()).filter(([, v]) => v !== ""));
    await api.post("/tasks", payload);
    await refresh();
    setShowNew(false);
  }

  async function markDone(task: TaskOut) {
    await api.patch(`/tasks/${task.id}`, { status: "TERMINE" });
    await refresh();
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
          <Button size="sm" onClick={() => setShowNew(!showNew)}><Plus size={14} /> Nouvelle action</Button>
        </CardHeader>

        <div className="mb-3 flex gap-2">
          {["", "A_FAIRE", "EN_COURS", "TERMINE", "ANNULE"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1 text-xs ${
                statusFilter === s ? "bg-mz-primary text-white" : "bg-mz-surface-2 text-mz-text-muted"
              }`}
            >
              {s === "" ? "Toutes" : STATUS_LABELS[s]?.label ?? s}
            </button>
          ))}
        </div>

        {showNew && (
          <form onSubmit={handleCreate} className="mb-4 space-y-1.5 rounded-mz-md border border-mz-border p-3">
            <input name="title" required placeholder="Titre de l'action" className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
            <div className="flex gap-1.5">
              <input name="due_date" type="date" className="w-1/2 rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
              <select name="priority" defaultValue="2" className="w-1/2 rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm">
                <option value="1">Priorité haute</option>
                <option value="2">Priorité normale</option>
                <option value="3">Priorité basse</option>
              </select>
            </div>
            <textarea name="comment" placeholder="Commentaire" rows={2} className="w-full rounded-mz-sm border border-mz-border bg-mz-input px-2 py-1 text-sm" />
            <Button type="submit" size="sm">Créer</Button>
          </form>
        )}

        <Table>
          <Thead>
            <Tr>
              <Th></Th>
              <Th>Action</Th>
              <Th>Échéance</Th>
              <Th>Priorité</Th>
              <Th>Statut</Th>
            </Tr>
          </Thead>
          <tbody>
            {tasks.map((t) => {
              const isLate = t.due_date && t.due_date < today && t.status !== "TERMINE";
              return (
                <Tr key={t.id}>
                  <Td>
                    {t.status !== "TERMINE" && (
                      <button onClick={() => markDone(t)} title="Marquer terminé">
                        <Check size={14} className="text-mz-text-muted hover:text-mz-success" />
                      </button>
                    )}
                  </Td>
                  <Td className="font-medium">{t.title}</Td>
                  <Td className={isLate ? "text-mz-danger" : "text-mz-text-muted"}>
                    {t.due_date ?? "—"} {isLate && "(en retard)"}
                  </Td>
                  <Td>{"!".repeat(4 - t.priority)}</Td>
                  <Td><Badge tone={STATUS_LABELS[t.status]?.tone ?? "neutral"}>{STATUS_LABELS[t.status]?.label ?? t.status}</Badge></Td>
                </Tr>
              );
            })}
            {tasks.length === 0 && (
              <Tr><Td colSpan={5} className="text-center text-mz-text-muted">Aucune action.</Td></Tr>
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
