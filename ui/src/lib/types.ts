// Types TS miroir du contrat de câble backend jarvis-suit.
// Toute divergence ici casse l'intégration : respecter le contrat au caractère près.

/** Vocabulaire d'événements émis par le core (voir core/events.py -> EventType). */
export type EventType =
  | "wake_up"
  | "profile.loaded"
  | "desktop.action"
  | "mail.received"
  | "mail.triaged"
  | "agent.started"
  | "agent.finished"
  | "agent.failed"
  | "agent.escalated"
  | "briefing.ready"
  | "night.report_ready"
  | "permission.denied"
  | "budget.exceeded"
  | "system.health"
  | "notification";

/** Événement immuable diffusé sur le bus / REST / WebSocket. */
export interface Event {
  id: string;
  /** `type` peut être un EventType connu ou une string inconnue (tolérance amont). */
  type: EventType | string;
  /** Timestamp ISO8601 (UTC). */
  ts: string;
  source: string;
  correlation_id: string | null;
  payload: Record<string, unknown>;
}

/** Événement enrichi d'un numéro de séquence monotone (journal). */
export interface SeqEvent extends Event {
  seq: number;
}

/** Statut d'exécution d'un agent, aligné sur les événements agent.*. */
export type AgentStatus =
  | "idle"
  | "started"
  | "finished"
  | "failed"
  | "escalated";

export interface AgentLastRun {
  correlation_id: string;
  /** Statut de la dernière exécution (présent dans le DTO backend LastRunDTO). */
  status?: string;
  tokens: number;
  usd: number;
  ended_ts: string | null;
  error: string | null;
}

export interface Agent {
  name: string;
  mode: string;
  permissions: string[];
  enabled: boolean;
  status: AgentStatus;
  last_run: AgentLastRun | null;
}

/** GET /api/health */
export interface Health {
  mode: "mock" | "real";
  version: string;
  inference_backend: string;
  desktop_backend: string;
  placement_available: boolean;
}

/** GET /api/events?since=&limit= */
export interface EventsResponse {
  events: SeqEvent[];
  latest_seq: number;
}

/** POST /api/agents/{name}/run */
export interface RunAgentResponse {
  correlation_id: string;
  status: string;
  output: Record<string, unknown>;
}

/** Premier message WebSocket : instantané complet de l'état. */
export interface WsSnapshot {
  kind: "snapshot";
  agents: Agent[];
  events: SeqEvent[];
  latest_seq: number;
}

/** Messages WebSocket suivants : un nouvel événement. */
export interface WsEvent {
  kind: "event";
  event: SeqEvent;
}

export type WsMessage = WsSnapshot | WsEvent;
