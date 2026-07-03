// Sélecteur pur : dérive la boîte de réception triée du flux d'événements.
// Payload EXACT de `mail.triaged` :
//   { id, category, priority, summary, subject, sender }
import type { HudColor } from "./theme";
import type { SeqEvent } from "./types";

export interface InboxItem {
  id: string;
  category: string;
  priority: number;
  summary: string;
  subject: string;
  sender: string;
  // Enrichis par GET /api/inbox (les événements `mail.triaged` ne portent pas le
  // corps du brouillon ni le drapeau de correction — voir InboxPanel).
  draft?: string | null;
  corrected?: boolean;
}

/** Lecture défensive d'un champ string du payload. */
function str(payload: Record<string, unknown>, key: string): string {
  const v = payload[key];
  return typeof v === "string" ? v : "";
}

/** Lecture défensive d'un champ number du payload. */
function num(payload: Record<string, unknown>, key: string): number {
  const v = payload[key];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/**
 * Dérive la boîte de réception à partir des événements `mail.triaged`.
 * - dédup par `id` : on garde l'occurrence la plus récente (plus grand `seq`) ;
 * - tri final par `priority` décroissante (les plus urgents en tête).
 * Fonction pure : n'observe que ses entrées.
 */
export function selectInbox(events: SeqEvent[]): InboxItem[] {
  const bySeq = new Map<string, { seq: number; item: InboxItem }>();

  for (const ev of events) {
    if (ev.type !== "mail.triaged") continue;
    const id = str(ev.payload, "id") || ev.id;
    const item: InboxItem = {
      id,
      category: str(ev.payload, "category"),
      priority: num(ev.payload, "priority"),
      summary: str(ev.payload, "summary"),
      subject: str(ev.payload, "subject"),
      sender: str(ev.payload, "sender"),
    };
    const prev = bySeq.get(id);
    if (!prev || ev.seq > prev.seq) bySeq.set(id, { seq: ev.seq, item });
  }

  return Array.from(bySeq.values())
    .map((e) => e.item)
    .sort((a, b) => b.priority - a.priority);
}

/** Couleur HUD d'une catégorie de mail (source de vérité pour composants + tests). */
export function categoryColor(category: string): HudColor {
  switch (category) {
    case "urgent":
      return "red";
    case "action":
      return "amber";
    case "info":
      return "cyan";
    case "newsletter":
    case "spam":
      return "gray";
    default:
      return "gray";
  }
}
