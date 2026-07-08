// Sélecteur pur : dérive le fil d'une conversation multi-tours du flux d'événements.
// Payload EXACT de `chat.message` :
//   { conversation_id, agent, role: "user" | "assistant", text }
import type { SeqEvent } from "./types";

export interface ConversationMessage {
  id: string;
  role: string;
  text: string;
}

/** Lecture défensive d'un champ string du payload. */
function str(payload: Record<string, unknown>, key: string): string {
  const v = payload[key];
  return typeof v === "string" ? v : "";
}

/**
 * Construit le transcript oldest→newest d'une conversation à partir des
 * événements `chat.message` dont `payload.conversation_id === conversationId`.
 * Les événements arrivent les plus récents en tête (avec un `seq`) → on trie
 * par `seq` croissant pour l'affichage. Fonction pure : n'observe que ses entrées.
 */
export function selectChatMessages(
  events: SeqEvent[],
  conversationId: string,
): ConversationMessage[] {
  const msgs: { seq: number; msg: ConversationMessage }[] = [];

  for (const ev of events) {
    if (ev.type !== "chat.message") continue;
    if (str(ev.payload, "conversation_id") !== conversationId) continue;
    const text = str(ev.payload, "text");
    const role = str(ev.payload, "role");
    if (!role) continue;
    msgs.push({ seq: ev.seq, msg: { id: ev.id, role, text } });
  }

  return msgs.sort((a, b) => a.seq - b.seq).map((m) => m.msg);
}
