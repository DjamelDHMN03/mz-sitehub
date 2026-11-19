import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { UploadCloud, Check, X, Link2 } from "lucide-react";

interface MapFeatureOut {
  id: string;
  name: string | null;
  geometry_type: string;
  detected_code: string | null;
  has_geometry: boolean;
}

interface MapLayerOut {
  id: string;
  name: string;
  source_type: string;
  original_filename: string | null;
  is_visible: boolean;
  feature_count: number;
  created_at: string;
}

interface ImportResult {
  layer: MapLayerOut;
  features: MapFeatureOut[];
  features_without_geometry: number;
}

interface LinkSuggestion {
  feature_id: string;
  detected_code: string;
  existing_site_id: string | null;
  suggestion: "RATTACHER" | "NOUVEAU_SITE";
}

export default function ImportCartePage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [suggestions, setSuggestions] = useState<LinkSuggestion[]>([]);
  const [resolvedFeatureIds, setResolvedFeatureIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!result) return;
    api
      .get<LinkSuggestion[]>(`/map-layers/${result.layer.id}/link-suggestions`)
      .then(({ data }) => setSuggestions(data));
  }, [result]);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setIsUploading(true);
    setResult(null);
    setSuggestions([]);
    setResolvedFeatureIds(new Set());

    const formData = new FormData();
    formData.append("file", file);

    try {
      const { data } = await api.post<ImportResult>("/map-layers/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Échec de l'import.");
    } finally {
      setIsUploading(false);
    }
  }, []);

  async function resolveFeature(featureId: string, action: "CREER" | "IGNORER") {
    await api.post(`/map-layers/features/${featureId}/link`, { action });
    setResolvedFeatureIds((prev) => new Set(prev).add(featureId));
  }

  async function resolveFeatureLink(featureId: string, siteId: string) {
    await api.post(`/map-layers/features/${featureId}/link`, { action: "RATTACHER", site_id: siteId });
    setResolvedFeatureIds((prev) => new Set(prev).add(featureId));
  }

  return (
    <div className="space-y-6">
      <Card
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed py-12 text-center transition-colors ${
          isDragging ? "border-mz-primary bg-mz-primary/5" : "border-mz-border"
        }`}
      >
        <UploadCloud size={32} className="text-mz-text-muted" />
        <p className="text-sm text-mz-text">
          Glissez-déposez un fichier <strong>.kml</strong> ou <strong>.kmz</strong> ici
        </p>
        <label className="cursor-pointer">
          <span className="text-sm text-mz-primary underline">ou parcourir vos fichiers</span>
          <input
            type="file"
            accept=".kml,.kmz"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </label>
        {isUploading && <p className="text-xs text-mz-text-muted">Import en cours...</p>}
        {error && <p className="text-sm text-mz-danger">{error}</p>}
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Résultat de l'import — {result.layer.original_filename}</CardTitle>
          </CardHeader>
          <p className="mb-3 text-sm text-mz-text">
            {result.features.length} objet(s) extrait(s)
            {result.features_without_geometry > 0 && (
              <span className="text-mz-warning">
                {" "}
                ({result.features_without_geometry} sans géométrie exploitable)
              </span>
            )}
          </p>

          {suggestions.length === 0 && (
            <p className="text-sm text-mz-text-muted">
              Aucun code site détecté automatiquement dans ce fichier.
            </p>
          )}

          <ul className="space-y-2">
            {suggestions.map((s) => {
              const isResolved = resolvedFeatureIds.has(s.feature_id);
              return (
                <li
                  key={s.feature_id}
                  className="flex items-center justify-between rounded-mz-md border border-mz-border bg-mz-surface-2 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-mz-text">{s.detected_code}</span>
                    {s.suggestion === "RATTACHER" ? (
                      <Badge tone="info">Rattacher au site existant</Badge>
                    ) : (
                      <Badge tone="warning">Nouveau site détecté</Badge>
                    )}
                  </div>

                  {isResolved ? (
                    <span className="text-xs text-mz-success">Traité</span>
                  ) : (
                    <div className="flex gap-1.5">
                      {s.suggestion === "NOUVEAU_SITE" && (
                        <Button size="sm" variant="secondary" onClick={() => resolveFeature(s.feature_id, "CREER")}>
                          <Check size={13} /> Créer
                        </Button>
                      )}
                      {s.suggestion === "RATTACHER" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            if (s.existing_site_id) resolveFeatureLink(s.feature_id, s.existing_site_id);
                          }}
                        >
                          <Link2 size={13} /> Rattacher
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => resolveFeature(s.feature_id, "IGNORER")}>
                        <X size={13} /> Ignorer
                      </Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}
