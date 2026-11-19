import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Table, Thead, Th, Tr, Td } from "@/components/Table";
import { UploadCloud, Download, Trash2, Share2, Sparkles } from "lucide-react";
import type { SiteListResponse } from "@/lib/types";

interface DocumentOut {
  id: string;
  category: string;
  filename: string;
  size_bytes: number | null;
  detected_code: string | null;
  version: number;
  created_at: string;
}

const CATEGORIES = [
  "DOC_B", "APS", "CONTRATS", "AUTORISATIONS", "PV", "PHOTOS",
  "CORRESPONDANCES", "CARTOGRAPHIE", "AUTRES",
];

interface ShareLinkOut {
  share_url: string;
  whatsapp_url: string | null;
  telegram_url: string | null;
  outlook_compose_url: string | null;
}

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function DocumentsPage() {
  const [sites, setSites] = useState<SiteListResponse | null>(null);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [ambiguity, setAmbiguity] = useState<{ reason: string } | null>(null);
  const [chosenCategory, setChosenCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [shareResult, setShareResult] = useState<ShareLinkOut | null>(null);

  useEffect(() => {
    api.get<SiteListResponse>("/sites", { params: { page_size: 200 } }).then(({ data }) => setSites(data));
  }, []);

  useEffect(() => {
    if (!selectedSiteId) return;
    refreshDocuments();
  }, [selectedSiteId]);

  async function refreshDocuments() {
    const { data } = await api.get<DocumentOut[]>(`/sites/${selectedSiteId}/documents`);
    setDocuments(data);
  }

  async function uploadFile(file: File, category?: string) {
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await api.post(
        `/sites/${selectedSiteId}/documents`,
        formData,
        { params: category ? { category } : {}, headers: { "Content-Type": "multipart/form-data" } }
      );
      setPendingFile(null);
      setAmbiguity(null);
      await refreshDocuments();
    } catch (err: any) {
      if (err?.response?.status === 422) {
        // Section 41 : ambigu -> on demande la catégorie à l'utilisateur plutôt que deviner
        setAmbiguity(err.response.data.detail);
        setPendingFile(file);
      } else {
        setError(err?.response?.data?.detail ?? "Échec de l'upload.");
      }
    }
  }

  async function handleDownload(doc: DocumentOut) {
    const response = await api.get(`/documents/${doc.id}/download`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = doc.filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  async function handleDelete(doc: DocumentOut) {
    await api.delete(`/documents/${doc.id}`);
    await refreshDocuments();
  }

  async function handleShare(doc: DocumentOut) {
    const { data } = await api.post<ShareLinkOut>("/shares", {
      document_ids: [doc.id],
      expiry_preset: "7d",
    });
    setShareResult(data);
  }

  async function handleIndex(doc: DocumentOut) {
    try {
      await api.post(`/rag/documents/${doc.id}/index`);
      setError(null);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          "Indexation impossible — vérifiez qu'Ollama est démarré (recherche documentaire, Phase 20)."
      );
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Site</CardTitle>
        </CardHeader>
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="w-full max-w-md rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm text-mz-text"
        >
          <option value="">— Choisir un site —</option>
          {sites?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.code} {s.name ? `— ${s.name}` : ""}</option>
          ))}
        </select>
      </Card>

      {selectedSiteId && (
        <>
          <Card
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) uploadFile(file);
            }}
            className="flex flex-col items-center gap-2 border-2 border-dashed py-8 text-center"
          >
            <UploadCloud size={28} className="text-mz-text-muted" />
            <p className="text-sm text-mz-text">Glissez-déposez un document, ou</p>
            <label className="cursor-pointer text-sm text-mz-primary underline">
              parcourir
              <input
                type="file"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadFile(file);
                }}
              />
            </label>
            {error && <p className="text-sm text-mz-danger">{error}</p>}
          </Card>

          {ambiguity && pendingFile && (
            <Card className="border-mz-warning">
              <p className="mb-2 text-sm text-mz-warning">
                Catégorie non détectée automatiquement pour « {pendingFile.name} » : {ambiguity.reason}
              </p>
              <div className="flex items-center gap-2">
                <select
                  value={chosenCategory}
                  onChange={(e) => setChosenCategory(e.target.value)}
                  className="rounded-mz-md border border-mz-border bg-mz-input px-2 py-1.5 text-sm"
                >
                  <option value="">Choisir une catégorie...</option>
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <Button
                  size="sm"
                  disabled={!chosenCategory}
                  onClick={() => pendingFile && uploadFile(pendingFile, chosenCategory)}
                >
                  Confirmer
                </Button>
              </div>
            </Card>
          )}

          {shareResult && (
            <Card className="border-mz-success">
              <p className="mb-2 text-sm text-mz-text">
                Lien créé (valide 7 jours) : <code className="text-xs">{shareResult.share_url}</code>
              </p>
              <div className="flex flex-wrap gap-2">
                {shareResult.whatsapp_url && (
                  <a href={shareResult.whatsapp_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="secondary">WhatsApp</Button>
                  </a>
                )}
                {shareResult.telegram_url && (
                  <a href={shareResult.telegram_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="secondary">Telegram</Button>
                  </a>
                )}
                {shareResult.outlook_compose_url && (
                  <a href={shareResult.outlook_compose_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="secondary">Outlook</Button>
                  </a>
                )}
                <Button size="sm" variant="ghost" onClick={() => navigator.clipboard.writeText(shareResult.share_url)}>
                  Copier le lien
                </Button>
              </div>
            </Card>
          )}

          <Table>
            <Thead>
              <Tr>
                <Th>Fichier</Th>
                <Th>Catégorie</Th>
                <Th>Code détecté</Th>
                <Th>Version</Th>
                <Th>Taille</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <tbody>
              {documents.map((doc) => (
                <Tr key={doc.id}>
                  <Td className="font-medium">{doc.filename}</Td>
                  <Td><Badge tone="info">{doc.category}</Badge></Td>
                  <Td className="text-mz-text-muted">{doc.detected_code ?? "—"}</Td>
                  <Td>V{doc.version}</Td>
                  <Td className="text-mz-text-muted text-xs">{formatSize(doc.size_bytes)}</Td>
                  <Td>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => handleDownload(doc)}>
                        <Download size={14} />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleShare(doc)}>
                        <Share2 size={14} />
                      </Button>
                      {doc.filename.toLowerCase().endsWith(".pdf") && (
                        <Button size="sm" variant="ghost" onClick={() => handleIndex(doc)} title="Indexer pour la recherche IA">
                          <Sparkles size={14} />
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(doc)}>
                        <Trash2 size={14} className="text-mz-danger" />
                      </Button>
                    </div>
                  </Td>
                </Tr>
              ))}
              {documents.length === 0 && (
                <Tr><Td colSpan={6} className="text-center text-mz-text-muted">Aucun document pour ce site.</Td></Tr>
              )}
            </tbody>
          </Table>
        </>
      )}
    </div>
  );
}
