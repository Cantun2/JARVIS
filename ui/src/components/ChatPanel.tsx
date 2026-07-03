import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { sayToEcho } from "../lib/api";
import { selectChat, type ChatMessage } from "../lib/chat";
import type { SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
}

/**
 * Chat JARVIS : façade d'ECHO. Le fil de conversation est dérivé des événements
 * voix (`voice.heard`/`voice.spoke`) — les nouvelles réponses arrivent via le
 * WebSocket. On tape une commande ; le bouton micro est un jalon (STT réel à venir).
 */
export default function ChatPanel({ events }: Props): JSX.Element {
  const messages = selectChat(events);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  async function send(): Promise<void> {
    const utterance = text.trim();
    if (!utterance || sending) return;
    setSending(true);
    setError(null);
    setPending(utterance);
    try {
      await sayToEcho(utterance);
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'envoi");
    } finally {
      setSending(false);
      setPending(null);
    }
  }

  return (
    <section
      className="hud-panel flex min-h-0 flex-col"
      aria-label="Chat JARVIS"
      data-testid="chat-panel"
    >
      <header className="flex items-center justify-between gap-2 border-b border-hud-border px-3 py-2">
        <h2 className="hud-label">Chat JARVIS</h2>
        <span className="text-[10px] text-hud-muted">
          Dis « Jarvis, … » pour lui parler
        </span>
      </header>

      {error && (
        <div className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red" role="alert">
          {error}
        </div>
      )}

      {messages.length === 0 ? (
        <div
          className="flex flex-1 items-center justify-center p-6 text-center text-xs text-hud-muted"
          data-testid="chat-empty"
        >
          Aucune conversation — essaie « Jarvis, fais-moi le briefing »
        </div>
      ) : (
        <ul
          className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3"
          data-testid="chat-log"
        >
          <AnimatePresence initial={false}>
            {messages.map((m) => (
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
          placeholder={pending ?? "Jarvis, …"}
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

function ChatBubble({ message }: { message: ChatMessage }): JSX.Element {
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
        {!isUser && (message.routedTo || message.spoke) && (
          <div className="mt-1 flex items-center gap-2 text-[10px] text-hud-muted">
            {message.routedTo && (
              <span className="rounded border border-hud-amber/40 px-1 text-hud-amber" data-testid="chat-routed">
                → {message.routedTo}
              </span>
            )}
            {message.spoke && <span data-testid="chat-spoken">🔊 parlé</span>}
          </div>
        )}
      </div>
    </div>
  );
}
