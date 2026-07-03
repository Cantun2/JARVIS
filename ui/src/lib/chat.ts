// Sélecteur pur : dérive le fil de conversation JARVIS du flux d'événements.
// Payloads EXACTS :
//   voice.heard : { transcript, wake, command }   (source ECHO)
//   voice.spoke : { text, intent, routed_to }      (source ECHO ou ORACLE)
import type { SeqEvent } from "./types";

export interface ChatMessage {
  id: string;
  seq: number;
  role: "user" | "jarvis";
  text: string;
  routedTo?: string | null;
  spoke?: boolean;
}

/** Lecture défensive d'un champ string du payload. */
function str(payload: Record<string, unknown>, key: string): string {
  const v = payload[key];
  return typeof v === "string" ? v : "";
}

/**
 * Construit le transcript oldest→newest à partir des événements voix.
 * - `voice.heard` (rôle « user ») : uniquement quand le wake-word est détecté
 *   (JARVIS ne « répond » qu'aux commandes qui lui sont adressées) ;
 * - `voice.spoke` (rôle « jarvis ») : la réponse parlée, avec l'agent déclencheur.
 * Fonction pure : n'observe que ses entrées. Les événements arrivent les plus
 * récents en tête → on trie par `seq` croissant pour l'affichage.
 */
export function selectChat(events: SeqEvent[]): ChatMessage[] {
  const msgs: ChatMessage[] = [];

  for (const ev of events) {
    if (ev.type === "voice.heard") {
      const wake = ev.payload.wake === true;
      if (!wake) continue;
      const text = str(ev.payload, "command") || str(ev.payload, "transcript");
      if (!text) continue;
      msgs.push({ id: ev.id, seq: ev.seq, role: "user", text });
    } else if (ev.type === "voice.spoke") {
      const text = str(ev.payload, "text");
      if (!text) continue;
      msgs.push({
        id: ev.id,
        seq: ev.seq,
        role: "jarvis",
        text,
        routedTo: str(ev.payload, "routed_to") || null,
        spoke: true,
      });
    }
  }

  return msgs.sort((a, b) => a.seq - b.seq);
}
