import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import SiteVisitModal, { SiteVisit, VisitType } from "@/components/SiteVisitModal";
import { ChevronLeft, ChevronRight, Pencil, Plus, Trash2 } from "lucide-react";

interface TaskOut {
  id: string;
  title: string;
  due_date: string | null;
  status: string;
}

const WEEKDAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const MONTHS = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

const TYPE_CHIP: Record<VisitType, string> = {
  TSS: "bg-sky-500/15 text-sky-400",
  CCT: "bg-amber-500/15 text-amber-400",
};

// Date locale -> "AAAA-MM-JJ" (sans passer par l'UTC, qui décale d'un jour)
function ymd(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function fromYmd(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function getMonthGrid(year: number, month: number): (Date | null)[] {
  const firstDay = new Date(year, month, 1);
  const startWeekday = (firstDay.getDay() + 6) % 7; // Lundi = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (Date | null)[] = Array(startWeekday).fill(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function visitLines(v: SiteVisit): { label: string; value: string }[] {
  const lines: { label: string; value: string | null }[] =
    v.visit_type === "TSS"
      ? [
          { label: "BET présent", value: v.bet_name },
          { label: "Ingénieur Radio présent", value: v.radio_engineer_name },
          { label: "Civil Work présent", value: v.civil_work_name },
          { label: "Négociateur", value: v.negotiator_name },
          { label: "Transmission présent", value: v.transmission_name },
        ]
      : [
          { label: "Lieu de rencontre", value: v.location },
          { label: "Civil Work", value: v.civil_work_name },
          { label: "Transmission", value: v.transmission_name },
          { label: "Négociateur", value: v.negotiator_name },
          { label: "BET", value: v.bet_name },
        ];
  if (v.observation) lines.push({ label: "Observation", value: v.observation });
  return lines.filter((l): l is { label: string; value: string } => Boolean(l.value));
}

export default function CalendrierPage() {
  const [current, setCurrent] = useState(new Date());
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [visits, setVisits] = useState<SiteVisit[]>([]);
  const [selected, setSelected] = useState<string | null>(ymd(new Date()));
  const [modal, setModal] = useState<{ type: VisitType; visit: SiteVisit | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const year = current.getFullYear();
  const month = current.getMonth();

  useEffect(() => {
    const start = ymd(new Date(year, month, 1));
    const end = ymd(new Date(year, month + 1, 0));
    api
      .get<{ items: TaskOut[]; total: number }>("/tasks", { params: { due_after: start, due_before: end, page_size: 200 } })
      .then(({ data }) => setTasks(data.items))
      .catch(() => setTasks([]));
  }, [year, month]);

  const loadVisits = useCallback(() => {
    const start = ymd(new Date(year, month, 1));
    const end = ymd(new Date(year, month + 1, 0));
    api
      .get<SiteVisit[]>("/site-visits", { params: { date_from: start, date_to: end } })
      .then(({ data }) => setVisits(data))
      .catch(() => setVisits([]));
  }, [year, month]);

  useEffect(() => {
    loadVisits();
  }, [loadVisits]);

  const tasksByDay = useMemo(() => {
    const map = new Map<string, TaskOut[]>();
    for (const t of tasks) {
      if (!t.due_date) continue;
      const list = map.get(t.due_date) ?? [];
      list.push(t);
      map.set(t.due_date, list);
    }
    return map;
  }, [tasks]);

  const visitsByDay = useMemo(() => {
    const map = new Map<string, SiteVisit[]>();
    for (const v of visits) {
      const list = map.get(v.visit_date) ?? [];
      list.push(v);
      map.set(v.visit_date, list);
    }
    return map;
  }, [visits]);

  async function deleteVisit(v: SiteVisit) {
    if (!window.confirm(`Supprimer la ${v.visit_type} du site ${v.site_code} ?`)) return;
    setError(null);
    try {
      await api.delete(`/site-visits/${v.id}`);
      loadVisits();
    } catch {
      setError("Suppression impossible. Vérifiez vos droits puis réessayez.");
    }
  }

  const cells = getMonthGrid(year, month);
  const todayStr = ymd(new Date());
  const selectedVisits = selected ? visitsByDay.get(selected) ?? [] : [];
  const selectedTasks = selected ? tasksByDay.get(selected) ?? [] : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-mz-text">{MONTHS[month]} {year}</h2>
        <div className="flex gap-1">
          <Button size="sm" variant="secondary" onClick={() => setCurrent(new Date(year, month - 1, 1))}>
            <ChevronLeft size={14} />
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setCurrent(new Date());
              setSelected(ymd(new Date()));
            }}
          >
            Aujourd'hui
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setCurrent(new Date(year, month + 1, 1))}>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      <div className="flex gap-3 text-xs text-mz-text-muted">
        <span className={`rounded-mz-sm px-1.5 py-0.5 ${TYPE_CHIP.TSS}`}>TSS</span>
        <span className={`rounded-mz-sm px-1.5 py-0.5 ${TYPE_CHIP.CCT}`}>CCT</span>
        <span className="rounded-mz-sm bg-mz-primary/15 px-1.5 py-0.5 text-mz-primary">Tâche</span>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {WEEKDAYS.map((d) => (
          <div key={d} className="text-center text-xs font-semibold uppercase text-mz-text-muted">{d}</div>
        ))}

        {cells.map((date, idx) => {
          if (!date) return <div key={idx} />;
          const dateStr = ymd(date);
          const dayTasks = tasksByDay.get(dateStr) ?? [];
          const dayVisits = visitsByDay.get(dateStr) ?? [];
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selected;
          const total = dayVisits.length + dayTasks.length;

          return (
            <Card
              key={idx}
              className={`min-h-[90px] p-2 ${isSelected ? "ring-2 ring-mz-primary" : isToday ? "border-mz-primary" : ""}`}
            >
              <div
                role="button"
                tabIndex={0}
                className="min-h-[70px] cursor-pointer"
                onClick={() => setSelected(dateStr)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(dateStr);
                  }
                }}
              >
                <p className={`mb-1 text-xs ${isToday ? "font-bold text-mz-primary" : "text-mz-text-muted"}`}>
                  {date.getDate()}
                </p>
                <div className="space-y-1">
                  {dayVisits.slice(0, 3).map((v) => (
                    <p key={v.id} className={`truncate rounded-mz-sm px-1 py-0.5 text-[11px] ${TYPE_CHIP[v.visit_type]}`}>
                      {v.visit_type} · {v.site_code}
                    </p>
                  ))}
                  {dayTasks.slice(0, Math.max(0, 3 - dayVisits.length)).map((t) => (
                    <p key={t.id} className="truncate rounded-mz-sm bg-mz-primary/15 px-1 py-0.5 text-[11px] text-mz-primary">
                      {t.title}
                    </p>
                  ))}
                  {total > 3 && (
                    <p className="text-[11px] text-mz-text-disabled">+{total - 3} autre(s)</p>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {selected && (
        <Card className="space-y-4 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-medium capitalize text-mz-text">
              {fromYmd(selected).toLocaleDateString("fr-FR", {
                weekday: "long", day: "numeric", month: "long", year: "numeric",
              })}
            </h3>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => setModal({ type: "TSS", visit: null })}>
                <Plus size={14} /> TSS
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setModal({ type: "CCT", visit: null })}>
                <Plus size={14} /> CCT
              </Button>
            </div>
          </div>

          {error && <p className="text-sm text-mz-danger">{error}</p>}

          {selectedVisits.length === 0 && selectedTasks.length === 0 && (
            <p className="text-sm text-mz-text-muted">Rien de prévu ce jour-là.</p>
          )}

          {selectedVisits.map((v) => (
            <div key={v.id} className="rounded-mz-md border border-mz-border p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-mz-text">
                  <span className={`mr-2 rounded-mz-sm px-1.5 py-0.5 text-xs ${TYPE_CHIP[v.visit_type]}`}>
                    {v.visit_type}
                  </span>
                  {v.site_code}
                </p>
                <div className="flex gap-1">
                  <Button size="sm" variant="secondary" onClick={() => setModal({ type: v.visit_type, visit: v })}>
                    <Pencil size={14} />
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => deleteVisit(v)}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
              <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
                {visitLines(v).map((l) => (
                  <div key={l.label} className="flex gap-2">
                    <dt className="text-mz-text-muted">{l.label} :</dt>
                    <dd className="text-mz-text">{l.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}

          {selectedTasks.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-mz-text-muted">Tâches</p>
              <ul className="space-y-1">
                {selectedTasks.map((t) => (
                  <li key={t.id} className="text-sm text-mz-text">{t.title}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {modal && selected && (
        <SiteVisitModal
          type={modal.type}
          visit={modal.visit}
          date={selected}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            loadVisits();
          }}
        />
      )}
    </div>
  );
}
