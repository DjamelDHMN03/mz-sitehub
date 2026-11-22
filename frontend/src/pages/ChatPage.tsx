import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/Button";

interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
}

const POLL_MS = 4000;
const MAX_LENGTH = 2000;

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : "Une erreur est survenue. R\u00e9essayez.";
}

export default function ChatPage() {
  const { user } = useAuth();
  const myId = (user as { id?: string } | null)?.id ?? null;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const stickToBottom = useRef(true);
  const lastCreatedAt = useRef<string | null>(null);

  const addMessages = useCallback((incoming: ChatMessage[]) => {
    setMessages((prev) => {
      const known = new Set(prev.map((m) => m.id));
      const fresh = incoming.filter((m) => !known.has(m.id));
      if (fresh.length === 0) return prev;
      return [...prev, ...fresh].sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
    });
  }, []);

  const poll = useCallback(async () => {
    try {
      const { data } = await api.get<ChatMessage[]>("/chat/messages", {
        params: lastCreatedAt.current ? { after: lastCreatedAt.current } : { limit: 100 },
      });
      if (data.length > 0) {
        lastCreatedAt.current = data[data.length - 1].created_at;
        addMessages(data);
      }
      setError(null);
    } catch {
      setError("Connexion au chat impossible. Nouvelle tentative...");
    } finally {
      setIsLoading(false);
    }
  }, [addMessages]);

  useEffect(() => {
    poll();
    const timer = setInterval(() => {
      if (!document.hidden) poll();
    }, POLL_MS);
    const onVisible = () => {
      if (!document.hidden) poll();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [poll]);

  useEffect(() => {
    const el = listRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  function onScroll() {
    const el = listRef.current;
    if (!el) return;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  async function send() {
    const content = draft.trim();
    if (!content || isSending) return;
    setIsSending(true);
    try {
      const { data } = await api.post<ChatMessage>("/chat/messages", { content });
      stickToBottom.current = true;
      addMessages([data]);
      setDraft("");
      setError(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setIsSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-mz-lg border border-mz-border bg-mz-card">
      <div ref={listRef} onScroll={onScroll} className="flex-1 space-y-3 overflow-y-auto p-4">
        {isLoading && <p className="text-sm text-mz-text-muted">Chargement...</p>}
        {!isLoading && messages.length === 0 && (
          <p className="text-sm text-mz-text-muted">{"Aucun message. \u00c9crivez le premier !"}</p>
        )}
        {messages.map((m) => {
          const mine = myId !== null && m.sender_id === myId;
          return (
            <div key={m.id} className={mine ? "flex justify-end" : "flex justify-start"}>
              <div
                className={
                  "max-w-[75%] rounded-mz-lg px-3 py-2 " + (mine ? "bg-mz-primary/20" : "bg-mz-surface-2")
                }
              >
                <p className="text-xs font-semibold text-mz-text">
                  {m.sender_name}{" "}
                  <span className="font-normal text-mz-text-muted">{formatTime(m.created_at)}</span>
                </p>
                <p className="whitespace-pre-wrap break-words text-sm text-mz-text">{m.content}</p>
              </div>
            </div>
          );
        })}
      </div>

      {error && <p className="px-4 pb-1 text-xs text-mz-danger">{error}</p>}

      <div className="flex items-end gap-2 border-t border-mz-border p-3">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          maxLength={MAX_LENGTH}
          placeholder={"\u00c9crivez un message (Entr\u00e9e pour envoyer, Maj+Entr\u00e9e pour une nouvelle ligne)"}
          className="flex-1 resize-none rounded-mz-md border border-mz-border bg-mz-input px-3 py-2 text-sm text-mz-text outline-none focus:border-mz-primary"
        />
        <Button onClick={send} disabled={isSending || draft.trim().length === 0}>
          <Send size={15} /> Envoyer
        </Button>
      </div>
    </div>
  );
}