import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Bot, Send, Check, X, Map as MapIcon } from "lucide-react";

interface PendingAction {
  action: string;
  params: Record<string, string>;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: unknown;
  pendingAction?: PendingAction;
  mapAction?: { map_action: "show" | "hide"; status?: string; wilaya?: string };
}

const QUICK_COMMANDS = [
  "Fais le point sur l\u2019avancement", "Quelles priorit\u00e9s cette semaine ?",
  "Sites bloqués", "Contrats qui expirent bientôt", "Sites sans GPS",
  "Résume AL6328", "Sites à relancer",
];

interface RagResult {
  content: string;
  document_filename: string;
  page_number: number | null;
  score: number;
}

export default function AssistantPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Bonjour ! Que souhaitez-vous savoir sur vos sites ?" },
  ]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [ragMode, setRagMode] = useState(false);
  const [ragResults, setRagResults] = useState<RagResult[] | null>(null);
  const [ragError, setRagError] = useState<string | null>(null);

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setIsSending(true);

    try {
      const { data } = await api.post("/assistant/chat", {
        message: text,
        conversation_id: conversationId,
        history: messages.slice(-8).map((m) => ({ role: m.role, content: m.content })),
      });
      setConversationId(data.conversation_id);

      const mapAction = data.data?.map_action ? data.data : undefined;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, data: data.data, pendingAction: data.pending_action, mapAction },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Une erreur est survenue. Réessayez." }]);
    } finally {
      setIsSending(false);
    }
  }

  async function confirmAction(action: PendingAction, messageIndex: number) {
    await api.post("/assistant/confirm-action", action);
    setMessages((prev) =>
      prev.map((m, i) => (i === messageIndex ? { ...m, pendingAction: undefined, content: m.content + "\n\n✅ Confirmé et appliqué." } : m))
    );
  }

  function cancelAction(messageIndex: number) {
    setMessages((prev) =>
      prev.map((m, i) => (i === messageIndex ? { ...m, pendingAction: undefined, content: m.content + "\n\n❌ Annulé." } : m))
    );
  }

  function goToMap(mapAction: NonNullable<ChatMessage["mapAction"]>) {
    const params = new URLSearchParams();
    if (mapAction.status) params.set("status", mapAction.status);
    if (mapAction.wilaya) params.set("wilaya", mapAction.wilaya);
    navigate(`/carte?${params.toString()}`);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (ragMode) {
      handleRagSearch(input);
    } else {
      sendMessage(input);
    }
  }

  async function handleRagSearch(query: string) {
    if (!query.trim()) return;
    setRagError(null);
    setRagResults(null);
    setIsSending(true);
    try {
      const { data } = await api.post<RagResult[]>("/rag/search", { query, top_k: 5 });
      setRagResults(data);
    } catch (err: any) {
      setRagError(
        err?.response?.status === 500 || err?.code === "ECONNREFUSED"
          ? "Recherche indisponible — Ollama n'est probablement pas démarré."
          : "Erreur lors de la recherche documentaire."
      );
    } finally {
      setIsSending(false);
      setInput("");
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-2xl flex-col">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {QUICK_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              onClick={() => sendMessage(cmd)}
              className="rounded-full border border-mz-border bg-mz-surface-2 px-3 py-1 text-xs text-mz-text-muted hover:text-mz-text"
            >
              {cmd}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-mz-text-muted">
          <input type="checkbox" checked={ragMode} onChange={(e) => setRagMode(e.target.checked)} />
          Rechercher dans les documents
        </label>
      </div>

      {ragMode && (
        <div className="mb-3 space-y-2">
          {ragError && <p className="text-sm text-mz-danger">{ragError}</p>}
          {ragResults && ragResults.length === 0 && (
            <p className="text-sm text-mz-text-muted">Aucun résultat pertinent trouvé dans les documents indexés.</p>
          )}
          {ragResults?.map((r, i) => (
            <Card key={i} className="text-sm">
              <p className="text-mz-text">{r.content}</p>
              <p className="mt-1 text-xs text-mz-text-muted">
                Source : {r.document_filename}{r.page_number ? `, page ${r.page_number}` : ""} (pertinence {(r.score * 100).toFixed(0)}%)
              </p>
            </Card>
          ))}
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <Card
              className={`max-w-[80%] whitespace-pre-line text-sm ${
                msg.role === "user" ? "bg-mz-primary/15 text-mz-text" : "bg-mz-surface-2"
              }`}
            >
              {msg.role === "assistant" && <Bot size={14} className="mb-1 text-mz-primary" />}
              {msg.content}

              {msg.pendingAction && (
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => confirmAction(msg.pendingAction!, i)}>
                    <Check size={13} /> Confirmer
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => cancelAction(i)}>
                    <X size={13} /> Annuler
                  </Button>
                </div>
              )}

              {msg.mapAction && (
                <div className="mt-2">
                  <Button size="sm" variant="secondary" onClick={() => goToMap(msg.mapAction!)}>
                    <MapIcon size={13} /> Voir sur la carte
                  </Button>
                </div>
              )}
            </Card>
          </div>
        ))}
        {isSending && <p className="text-xs text-mz-text-muted">MZ Assistant réfléchit...</p>}
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={ragMode ? "Rechercher dans les documents indexés..." : "Que souhaitez-vous faire ?"}
          className="flex-1 rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary"
        />
        <Button type="submit" disabled={isSending}>
          <Send size={14} />
        </Button>
      </form>
    </div>
  );
}
