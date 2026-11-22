import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";

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

export default function NegociateursPage() {
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

  return (
    <div className="space-y-4">
      <p className="text-sm text-mz-text-muted">
        {"Sites assign\u00e9s par n\u00e9gociateur (hors corbeille). Cliquez sur un nom pour voir ses sites."}
      </p>
      {error && <p className="text-sm text-mz-danger">Statistiques indisponibles.</p>}
      {!error && rows === null && <p className="text-sm text-mz-text-muted">Chargement...</p>}
      {rows && rows.length === 0 && (
        <p className="text-sm text-mz-text-muted">{"Aucun site assign\u00e9."}</p>
      )}
      {rows && rows.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th>{"N\u00e9gociateur"}</Th>
              <Th>{"Assign\u00e9s"}</Th>
              <Th>En cours</Th>
              <Th>{"N\u00e9gociation"}</Th>
              <Th>{"Valid\u00e9s"}</Th>
              <Th>{"Bloqu\u00e9s"}</Th>
            </Tr>
          </Thead>          <tbody>
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