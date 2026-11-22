import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";

interface NegociateurStats {
  user_id: string | null;
  full_name: string;
  assignes: number;
  en_cours: number;
  negociation: number;
  valides: number;
  bloques: number;
}

const REFRESH_MS = 60000;

function Stat({ label, value, alert }: { label: string; value: number; alert?: boolean }) {
  return (
    <span className="flex flex-col items-center">
      <span
        className={
          alert && value > 0 ? "text-sm font-semibold text-mz-danger" : "text-sm font-semibold text-mz-text"
        }
      >
        {value}
      </span>
      <span>{label}</span>
    </span>
  );
}

export function NegociateursStats() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const activeId = searchParams.get("responsable");
  const [rows, setRows] = useState<NegociateurStats[] | null>(null);
  const [error, setError] = useState(false);

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

  function toggle(id: string | null) {
    if (!id) return;
    navigate(activeId === id ? "/sites" : `/sites?responsable=${id}`);
  }

  return (
    <div className="max-h-64 overflow-y-auto border-t border-mz-border px-3 py-3">
      <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-mz-text-muted">
        {"N\u00e9gociateurs"}
      </p>
      {error && <p className="px-2 text-xs text-mz-danger">Statistiques indisponibles.</p>}
      {!error && rows === null && <p className="px-2 text-xs text-mz-text-muted">Chargement...</p>}
      {rows && rows.length === 0 && (
        <p className="px-2 text-xs text-mz-text-muted">{"Aucun site assign\u00e9."}</p>
      )}
      <ul className="space-y-1">
        {(rows ?? []).map((r) => {
          const selected = r.user_id !== null && r.user_id === activeId;
          return (
            <li key={r.user_id ?? "none"}>
              <button
                type="button"
                onClick={() => toggle(r.user_id)}
                disabled={r.user_id === null}
                aria-pressed={selected}
                title={r.user_id ? "Voir les sites de ce n\u00e9gociateur" : undefined}
                className={
                  "w-full rounded-mz-md px-2 py-1.5 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary " +
                  (selected ? "bg-mz-primary/15" : "hover:bg-mz-surface-2 disabled:hover:bg-transparent")
                }
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-mz-text">{r.full_name}</span>
                  <span className="text-xs text-mz-text-muted" title={"Sites assign\u00e9s"}>
                    {r.assignes}
                  </span>
                </span>
                <span className="mt-1 grid grid-cols-4 gap-1 text-center text-[10px] text-mz-text-muted">
                  <Stat label="En cours" value={r.en_cours} />
                  <Stat label={"N\u00e9go."} value={r.negociation} />
                  <Stat label={"Valid\u00e9s"} value={r.valides} />
                  <Stat label={"Bloqu\u00e9s"} value={r.bloques} alert />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}