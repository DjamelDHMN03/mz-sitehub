import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";

interface AuditLogOut {
  id: number;
  user_email: string | null;
  entity: string;
  entity_id: string | null;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  occurred_at: string;
}

interface AuditLogPage {
  items: AuditLogOut[];
  total: number;
}

const ACTION_TONES: Record<string, "success" | "info" | "danger" | "warning" | "neutral"> = {
  CREATE: "success",
  UPDATE: "info",
  DELETE: "danger",
  RESTORE: "warning",
  UPLOAD: "success",
  REVOKE: "danger",
};

export default function HistoriquePage() {
  const [logs, setLogs] = useState<AuditLogOut[]>([]);
  const [total, setTotal] = useState(0);
  const [entities, setEntities] = useState<string[]>([]);
  const [entityFilter, setEntityFilter] = useState("");

  useEffect(() => {
    api.get<string[]>("/audit-logs/entities").then(({ data }) => setEntities(data));
  }, []);

  useEffect(() => {
    api
      .get<AuditLogPage>("/audit-logs", { params: entityFilter ? { entity: entityFilter } : {} })
      .then(({ data }) => {
        setLogs(data.items);
        setTotal(data.total);
      });
  }, [entityFilter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <select
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm"
        >
          <option value="">Toutes les entités</option>
          {entities.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <p className="text-sm text-mz-text-muted">{total} évènement(s)</p>
      </div>

      <Card className="p-0">
        <Table>
          <Thead>
            <Tr>
              <Th>Date</Th>
              <Th>Utilisateur</Th>
              <Th>Entité</Th>
              <Th>Action</Th>
              <Th>Détail</Th>
            </Tr>
          </Thead>
          <tbody>
            {logs.map((log) => (
              <Tr key={log.id}>
                <Td className="whitespace-nowrap text-xs text-mz-text-muted">
                  {new Date(log.occurred_at).toLocaleString("fr-FR")}
                </Td>
                <Td className="text-sm">{log.user_email ?? "Système"}</Td>
                <Td className="text-sm">{log.entity}</Td>
                <Td><Badge tone={ACTION_TONES[log.action] ?? "neutral"}>{log.action}</Badge></Td>
                <Td className="text-xs text-mz-text-muted">
                  {log.field && <span className="font-medium">{log.field} : </span>}
                  {log.old_value && <span className="line-through">{log.old_value}</span>}
                  {log.old_value && log.new_value && " → "}
                  {log.new_value}
                </Td>
              </Tr>
            ))}
            {logs.length === 0 && (
              <Tr><Td colSpan={5} className="text-center text-mz-text-muted">Aucun évènement.</Td></Tr>
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
