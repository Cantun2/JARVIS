import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { getChatHistory, postChat } from "../lib/api";
import { selectChatMessages, type ConversationMessage } from "../lib/conversation";
import type { Agent, ChatMsg, SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
  agents: Agent[];
  /** Agent sélectionné en externe (clic sur l'arc). Défaut : JARVIS. */
  agent?: string;
}

/**
 * Chat multi-tours avec un agent conversationnel. On choisit à QUI parler
 * (agents où `conversational === true`) ; le fil vivant est dérivé des
 * événements `chat.message` (WebSocket) une fois la conversation identifiée.
 * Avant la première réponse on affiche une bulle optimiste + un indicateur de
 * saisie. Le bouton micro est un jalon (STT réel à venir).
 */
export default function ChatPanel({ events, agents, agent }: Props): JSX.Element {
  const [activeAgent, setActiveAgent] = useState(agent ?? "JARVIS");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [backlog, setBacklog] = useState<ChatMsg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  const chatable = agents.filter((a) => a.conversational);

  // L'agent externe (clic sur l'arc) prime : on bascule la cible et on repart
  // d'une conversation neuve.
  useEffect(() => {
    setActiveAgent(agent ?? "JARVIS");
    setConversationId(null);
    setBacklog([]);
    setPending(null);
    setError(null);
  }, [agent]);

  // Une fois la conversation identifiée, on amorce le backlog via REST (utile
  // pour les historiques longs au-delà de la fenêtre WS). Best-effort.
  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    getChatHistory(conversationId)
      .then((h) => {
        if (!cancelled) setBacklog(h.messages);
      })
      .catch(() => {
        /* backlog best-effort : le fil vivant suffit */
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  function switchAgent(name: string): void {
    if (name === activeAgent) return;
    setActiveAgent(name);
    setConversationId(null);
    setBacklog([]);
    setPending(null);
    setError(null);
    setText("");
  }

  async function send(): Promise<void> {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    setError(null);
    setPending(message);
    try {
      const reply = await postChat(activeAgent, message, conversationId ?? undefined);
      setConversationId(reply.conversation_id);
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'envoi");
    } finally {
      setSending(false);
      setPending(null);
    }
  }

  // Fil affiché : on préfère le transcript vivant (WS) ; on retombe sur le
  // backlog REST seulement s'il contient davantage de messages.
  const live: ConversationMessage[] = conversationId
    ? selectChatMessages(events, conversationId)
    : [];
  const backlogMsgs: ConversationMessage[] = backlog.map((m, i) => ({
    id: `hist-${i}`,
    role: m.role,
    text: m.text,
  }));
  const history = backlogMsgs.length > live.length ? backlogMsgs : live;

  // Bulle optimiste : le message que l'on vient d'envoyer, tant que son écho WS
  // n'est pas encore arrivé.
  const lastUser = [...history].reverse().find((m) => m.role === "user")?.text;
  const showPending = pending !== null && lastUser !== pending;
  const view: ConversationMessage[] = showPending
    ? [...history, { id: "pending", role: "user", text: pending }]
    : history;

  return (
    <section
      className="hud-panel flex min-h-0 flex-col"
      aria-label="Chat JARVIS"
      data-testid="chat-panel"
    >
      <header className="flex items-center justify-between gap-2 border-b border-hud-border px-3 py-2">
        <h2 className="hud-label">
          Chat <span className="text-hud-cyan">{activeAgent}</span>
        </h2>
        <span className="text-[10px] text-hud-muted">Conversation multi-tours</span>
      </header>

      {chatable.length > 0 && (
        <div
          className="flex flex-wrap items-center gap-1.5 border-b border-hud-border px-3 py-2"
          data-testid="chat-agents"
          role="group"
          aria-label="Choisir l'agent"
        >
          {chatable.map((a) => {
            const selected = a.name === activeAgent;
            return (
              <button
                key={a.name}
                type="button"
                onClick={() => switchAgent(a.name)}
                aria-pressed={selected}
                data-testid={`chat-agent-${a.name}`}
                className={`hud-label rounded-md border px-2 py-1 transition ${
                  selected
                    ? "border-hud-cyan/50 bg-hud-cyan/10 text-hud-cyan"
                    : "border-transparent text-hud-muted hover:text-hud-text"
                }`}
              >
                {a.name}
              </button>
            );
          })}
        </div>
      )}

      {error && (
        <div className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red" role="alert">
          {error}
        </div>
      )}

      {view.length === 0 && !sending ? (
        <div
          className="flex flex-1 items-center justify-center p-6 text-center text-xs text-hud-muted"
          data-testid="chat-empty"
        >
          Aucune conversation — écris à {activeAgent} pour commencer
        </div>
      ) : (
        <ul
          className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3"
          data-testid="chat-log"
        >
          <AnimatePresence initial={false}>
            {view.map((m) => (
              <motion.li
                key={m.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
              >
                <ChatBubble message={m} />
              </motion.li>
            ))}
          </AnimatePresence>
          {sending && (
            <li>
              <div className="flex justify-start" data-testid="chat-typing">
                <div className="rounded-lg border border-hud-border bg-white/[0.02] px-3 py-1.5 text-xs text-hud-muted">
                  {activeAgent} écrit…
                </div>
              </div>
            </li>
          )}
        </ul>
      )}

      <form
        className="flex items-center gap-2 border-t border-hud-border px-3 py-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <button
          type="button"
          disabled
          title="Micro (à venir)"
          aria-label="Micro (à venir)"
          className="shrink-0 rounded border border-hud-border px-2 py-1 text-hud-muted opacity-60"
          data-testid="chat-mic"
        >
          🎙
        </button>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={pending ?? `Écris à ${activeAgent}…`}
          className="min-w-0 flex-1 rounded border border-hud-border bg-transparent px-2 py-1 text-xs text-hud-text placeholder:text-hud-muted focus:border-hud-cyan/50 focus:outline-none"
          data-testid="chat-input"
        />
        <button
          type="submit"
          disabled={sending || text.trim() === ""}
          className="shrink-0 rounded border border-hud-cyan/40 bg-hud-cyan/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-cyan transition hover:bg-hud-cyan/20 disabled:opacity-50"
          data-testid="chat-send"
        >
          {sending ? "…" : "Envoyer"}
        </button>
      </form>
    </section>
  );
}

function ChatBubble({ message }: { message: ConversationMessage }): JSX.Element {
  const isUser = message.role === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      data-testid="chat-message"
      data-role={message.role}
    >
      <div
        className={`max-w-[80%] rounded-lg border px-3 py-1.5 text-xs ${
          isUser
            ? "border-hud-cyan/30 bg-hud-cyan/10 text-hud-text"
            : "border-hud-border bg-white/[0.02] text-hud-text"
        }`}
      >
        <p className="leading-relaxed">{message.text}</p>
      </div>
    </div>
  );
}
