// Mappings couleur partagés (source de vérité pour composants + tests).
import type { Agent, AgentStatus, EventType, SeqEvent } from "./types";

/** Familles de couleur HUD (clés stables pour les tests). */
export type HudColor = "green" | "amber" | "red" | "gray" | "cyan";

/** Valeurs hex correspondantes (alignées sur tailwind.config.ts). */
export const HUD_HEX: Record<HudColor, string> = {
  green: "#34d399",
  amber: "#f59e0b",
  red: "#f87171",
  gray: "#64748b",
  cyan: "#22d3ee",
};

/**
 * Couleur d'un agent selon statut + activation.
 * vert = finished/idle, ambre = started/escalated, rouge = failed,
 * gris = désactivé (enabled=false) — la désactivation prime sur le statut.
 */
export function agentColor(status: AgentStatus, enabled: boolean): HudColor {
  if (!enabled) return "gray";
  switch (status) {
    case "finished":
    case "idle":
      return "green";
    case "started":
    case "escalated":
      return "amber";
    case "failed":
      return "red";
    default:
      return "gray";
  }
}

/** Couleur d'un badge de type d'événement. */
export function eventColor(type: EventType | string): HudColor {
  switch (type) {
    case "agent.finished":
    case "briefing.ready":
    case "night.report_ready":
    case "profile.loaded":
      return "green";
    case "agent.started":
    case "agent.escalated":
    case "mail.received":
    case "mail.triaged":
    case "wake_up":
      return "amber";
    case "agent.failed":
    case "permission.denied":
    case "budget.exceeded":
      return "red";
    case "system.health":
    case "desktop.action":
      return "cyan";
    case "notification":
    default:
      return "gray";
  }
}

/** Classes Tailwind (texte + fond léger + bordure) pour un badge coloré. */
export const HUD_BADGE_CLASS: Record<HudColor, string> = {
  green: "text-hud-green border-hud-green/40 bg-hud-green/10",
  amber: "text-hud-amber border-hud-amber/40 bg-hud-amber/10",
  red: "text-hud-red border-hud-red/40 bg-hud-red/10",
  gray: "text-hud-gray border-hud-gray/40 bg-hud-gray/10",
  cyan: "text-hud-cyan border-hud-cyan/40 bg-hud-cyan/10",
};

/** Classe de remplissage (pastilles d'agent). */
export const HUD_FILL_CLASS: Record<HudColor, string> = {
  green: "bg-hud-green",
  amber: "bg-hud-amber",
  red: "bg-hud-red",
  gray: "bg-hud-gray",
  cyan: "bg-hud-cyan",
};

/** agent.* -> statut. Retourne null pour les types non pertinents. */
export function statusFromEventType(type: string): AgentStatus | null {
  switch (type) {
    case "agent.started":
      return "started";
    case "agent.finished":
      return "finished";
    case "agent.failed":
      return "failed";
    case "agent.escalated":
      return "escalated";
    default:
      return null;
  }
}

/**
 * Superpose sur la liste d'agents le dernier statut déduit des événements
 * agent.* (identifiés par payload.agent | payload.name | source). Les
 * événements sont supposés triés du plus récent au plus ancien. Un agent
 * désactivé n'est jamais réactivé par un événement. Fonction pure.
 */
export function overlayAgentStatus(agents: Agent[], events: SeqEvent[]): Agent[] {
  if (events.length === 0) return agents;
  const latest = new Map<string, AgentStatus>();
  for (const ev of events) {
    const st = statusFromEventType(ev.type);
    if (!st) continue;
    const key =
      (typeof ev.payload.agent === "string" && ev.payload.agent) ||
      (typeof ev.payload.name === "string" && ev.payload.name) ||
      ev.source;
    if (key && !latest.has(key)) latest.set(key, st); // premier vu = plus récent
  }
  if (latest.size === 0) return agents;
  return agents.map((a) => {
    const st = latest.get(a.name);
    return st && a.enabled ? { ...a, status: st } : a;
  });
}

/** Résumé court et lisible d'un payload d'événement (1 ligne). */
export function summarizePayload(payload: Record<string, unknown>): string {
  const keys = Object.keys(payload);
  if (keys.length === 0) return "";
  // Champs "parlants" mis en avant s'ils existent.
  const preferred = ["message", "summary", "profile", "subject", "name", "error", "reason"];
  for (const key of preferred) {
    const v = payload[key];
    if (typeof v === "string" && v.length > 0) return v;
  }
  return keys
    .slice(0, 3)
    .map((k) => `${k}=${formatValue(payload[k])}`)
    .join(" · ");
}

function formatValue(v: unknown): string {
  if (v === null) return "null";
  if (typeof v === "string") return v.length > 40 ? `${v.slice(0, 37)}…` : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return `[${v.length}]`;
  if (typeof v === "object") return "{…}";
  return String(v);
}
