import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { UploadCloud } from "lucide-react";

interface PreviewItem {
  row_number: number;
  code: string | null;
  action: "CREATE" | "UPDATE" | "INCHANGE" | "IGNORE_NO_CODE";
  changes: Record<string, [unknown, unknown]>;
}

interface PreviewResult {
  import_id: string;
  detected_columns: Record<string, number>;
  unmatched_headers: string[];
  items: PreviewItem[];
  summary: Record<string, number>;
}

interface ConfirmResult {
  created: number;
  updated: number;
  warnings: string[];
}

const ACTION_BADGE: Record<string, "success" | "info" | "neutral" | "warning"> = {
  CREATE: "success",
  UPDATE: "info",
  INCHANGE: "neutral",
  IGNORE_NO_CODE: "warning",
};

export default function ImportExcelPage() {
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [confirmResult, setConfirmResult] = useState<ConfirmResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleFile(file: File) {
    setError(null);
    setConfirmResult(null);
    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await api.post<PreviewResult>("/import/excel/preview", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Échec de la lecture du fichier.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirm() {
    if (!preview) return;
    const { data } = await api.post<ConfirmResult>("/import/excel/confirm", {
      import_id: preview.import_id,
      apply_creates: true,
      apply_updates: true,
    });
    setConfirmResult(data);
    setPreview(null);
  }

  return (
    <div className="space-y-4">
      <Card
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        className="flex flex-col items-center gap-2 border-2 border-dashed py-10 text-center"
      >
        <UploadCloud size={28} className="text-mz-text-muted" />
        <p className="text-sm text-mz-text">Glissez-déposez un fichier Excel (.xlsx), ou</p>
        <label className="cursor-pointer text-sm text-mz-primary underline">
          parcourir
          <input
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </label>
        {isLoading && <p className="text-xs text-mz-text-muted">Lecture du fichier...</p>}
        {error && <p className="text-sm text-mz-danger">{error}</p>}
      </Card>

      {confirmResult && (
        <Card className="border-mz-success">
          <p className="text-sm text-mz-text">
            {confirmResult.created} site(s) créé(s), {confirmResult.updated} site(s) mis à jour.
          </p>
          {confirmResult.warnings.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs text-mz-warning">
              {confirmResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </Card>
      )}

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle>Prévisualisation avant import</CardTitle>
          </CardHeader>

          <div className="mb-3 flex gap-2">
            {Object.entries(preview.summary).map(([action, count]) => (
              <Badge key={action} tone={ACTION_BADGE[action]}>{action} : {count}</Badge>
            ))}
          </div>

          {preview.unmatched_headers.length > 0 && (
            <p className="mb-3 text-xs text-mz-text-muted">
              Colonnes non reconnues (ignorées) : {preview.unmatched_headers.join(", ")}
            </p>
          )}

          <div className="max-h-96 space-y-1 overflow-y-auto">
            {preview.items.map((item) => (
              <div key={item.row_number} className="flex items-center justify-between rounded-mz-md border border-mz-border px-3 py-1.5 text-sm">
                <span className="font-mono text-mz-text">{item.code ?? `Ligne ${item.row_number}`}</span>
                <Badge tone={ACTION_BADGE[item.action]}>{item.action}</Badge>
              </div>
            ))}
          </div>

          <div className="mt-4 flex gap-2">
            <Button onClick={handleConfirm}>Confirmer l'import</Button>
            <Button variant="ghost" onClick={() => setPreview(null)}>Annuler</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
