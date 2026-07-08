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
  | "backlog.ready"
  | "task.transitioned"
  | "permission.denied"
  | "budget.exceeded"
  | "system.health"
  | "voice.heard"
  | "voice.spoke"
  | "mail.drafted"
  | "mail.reclassified"
  | "chat.message"
  | "todo.created"
  | "todo.updated"
  | "reminder.due"
  | "appointment.upcoming"
  | "agent.proposal"
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
  /** True si l'agent tient une conversation multi-tours (POST /api/chat). */
  conversational: boolean;
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

// --- Mission Control ---------------------------------------------------------
// Miroir TS du contrat backend (projets / tâches / rapport de nuit).

/** Statut d'une tâche dans le kanban Mission Control. */
export type TaskStatus =
  | "backlog"
  | "in_progress"
  | "review"
  | "done"
  | "blocked"
  | "failed";

/** Tâche d'un projet (unité de travail agentique). */
export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  status: TaskStatus;
  report: string;
  diff: string;
  blocker: string | null;
  updated_ts: string;
}

/** Projet : objectif + comptage de tâches par statut. */
export interface Project {
  id: string;
  name: string;
  goal: string;
  created_ts: string;
  task_counts: Record<TaskStatus, number>;
}

/** Rapport de nuit : synthèse d'une exécution nocturne (éventuellement dry-run). */
export interface NightReport {
  date: string;
  done: number;
  blocked: number;
  failed: number;
  cost_usd: number;
  dry_run: boolean;
  tasks: { title: string; status: string; branch?: string; note?: string }[];
  blockers: string[];
}

/** POST /api/projects -> projet créé + backlog initial. */
export interface CreateProjectResponse {
  project: Project;
  tasks: Task[];
}

/** Action de transition applicable à une tâche. */
export type TaskAction = "approve" | "reject" | "retry";

// --- Phase 4 — Les sens (ECHO / brouillons) ----------------------------------
// Miroir TS du contrat de câble voix + mail enrichi.

/** POST /api/echo/say -> réponse d'ECHO (transcription + intent + réponse). */
export interface EchoReply {
  heard: string;
  wake_detected: boolean;
  intent: string;
  routed_to: string | null;
  response: string;
  spoke: boolean;
}

/** GET /api/inbox/drafts -> brouillon de réponse préparé pour un mail. */
export interface Draft {
  mail_id: string;
  sender: string;
  subject: string;
  body: string;
  created_ts: string;
}

/** Catégories de tri d'un mail (contrat POST /api/inbox/{id}/reclassify). */
export type MailCategory = "urgent" | "action" | "info" | "newsletter" | "spam";

/** Item enrichi de GET /api/inbox (contient brouillon + drapeau correction). */
export interface InboxItemDTO {
  id: string;
  sender: string;
  subject: string;
  category: string;
  priority: number;
  summary: string;
  draft: string | null;
  corrected: boolean;
}

/** GET /api/inbox -> liste enrichie + compteurs par catégorie. */
export interface InboxResponse {
  items: InboxItemDTO[];
  counts: Record<string, number>;
}

// --- Chat multi-tours (agents conversationnels) ------------------------------
// Miroir TS du contrat de câble POST /api/chat + GET /api/chat/{id} + /api/conversations.

/** Un message d'une conversation (historique REST). */
export interface ChatMsg {
  role: string;
  text: string;
  created_ts: string;
}

/** POST /api/chat -> réponse de l'agent conversationnel. */
export interface ChatReply {
  conversation_id: string;
  agent: string;
  reply: string;
  turns: number;
}

/** GET /api/chat/{conversation_id} -> historique complet d'une conversation. */
export interface ChatHistory {
  conversation_id: string;
  agent: string;
  messages: ChatMsg[];
}

/** GET /api/conversations?agent=NAME -> liste des conversations d'un agent. */
export interface Conversation {
  id: string;
  agent: string;
  title: string;
  updated_ts: string;
}

// --- Agenda (todos / rendez-vous / rappels) ----------------------------------
// Miroir TS du contrat de câble CHRONOS (TodoDTO).

/** Nature d'un élément d'agenda. */
export type TodoKind = "task" | "appointment";

/** Statut d'un élément d'agenda. */
export type TodoStatus = "pending" | "done" | "cancelled";

/** Élément d'agenda : tâche ou rendez-vous (miroir de TodoDTO). */
export interface Todo {
  id: string;
  kind: TodoKind;
  title: string;
  /** Date au format YYYY-MM-DD (heure locale). */
  date: string;
  /** Heure HH:MM ou null si non planifié. */
  time: string | null;
  notes: string;
  status: TodoStatus;
  remind_lead_min: number;
  reminded_ts: string | null;
  tags: string[];
  /** Suggestion écrite par CHRONOS (vide si aucune). */
  proposal: string;
  updated_ts: string;
}

/** Corps POST /api/todos. */
export interface CreateTodo {
  title: string;
  date: string;
  kind?: TodoKind;
  time?: string;
  notes?: string;
  remind_lead_min?: number;
  tags?: string[];
}

/** Corps PATCH /api/todos/{id} (champs partiels). */
export interface UpdateTodo {
  title?: string;
  date?: string;
  time?: string | null;
  notes?: string;
  kind?: TodoKind;
  remind_lead_min?: number;
  tags?: string[];
}
