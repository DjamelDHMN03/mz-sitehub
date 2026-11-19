import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { ChevronLeft, ChevronRight } from "lucide-react";

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

function getMonthGrid(year: number, month: number): (Date | null)[] {
  const firstDay = new Date(year, month, 1);
  const startWeekday = (firstDay.getDay() + 6) % 7; // Lundi = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (Date | null)[] = Array(startWeekday).fill(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export default function CalendrierPage() {
  const [current, setCurrent] = useState(new Date());
  const [tasks, setTasks] = useState<TaskOut[]>([]);

  const year = current.getFullYear();
  const month = current.getMonth();

  useEffect(() => {
    const start = new Date(year, month, 1).toISOString().slice(0, 10);
    const end = new Date(year, month + 1, 0).toISOString().slice(0, 10);
    api
      .get<{ items: TaskOut[]; total: number }>("/tasks", { params: { due_after: start, due_before: end, page_size: 200 } })
      .then(({ data }) => setTasks(data.items));
  }, [year, month]);

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

  const cells = getMonthGrid(year, month);
  const todayStr = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-mz-text">{MONTHS[month]} {year}</h2>
        <div className="flex gap-1">
          <Button size="sm" variant="secondary" onClick={() => setCurrent(new Date(year, month - 1, 1))}>
            <ChevronLeft size={14} />
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setCurrent(new Date())}>
            Aujourd'hui
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setCurrent(new Date(year, month + 1, 1))}>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {WEEKDAYS.map((d) => (
          <div key={d} className="text-center text-xs font-semibold uppercase text-mz-text-muted">{d}</div>
        ))}

        {cells.map((date, idx) => {
          if (!date) return <div key={idx} />;
          const dateStr = date.toISOString().slice(0, 10);
          const dayTasks = tasksByDay.get(dateStr) ?? [];
          const isToday = dateStr === todayStr;

          return (
            <Card key={idx} className={`min-h-[90px] p-2 ${isToday ? "border-mz-primary" : ""}`}>
              <p className={`mb-1 text-xs ${isToday ? "font-bold text-mz-primary" : "text-mz-text-muted"}`}>
                {date.getDate()}
              </p>
              <div className="space-y-1">
                {dayTasks.slice(0, 3).map((t) => (
                  <p key={t.id} className="truncate rounded-mz-sm bg-mz-primary/15 px-1 py-0.5 text-[11px] text-mz-primary">
                    {t.title}
                  </p>
                ))}
                {dayTasks.length > 3 && (
                  <p className="text-[11px] text-mz-text-disabled">+{dayTasks.length - 3} autre(s)</p>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
