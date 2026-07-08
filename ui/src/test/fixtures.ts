// Fabriques d'objets factices pour les tests (miroir du contrat de câble).
import type {
  Agent,
  AgentStatus,
  NightReport,
  Project,
  SeqEvent,
  Task,
  TaskStatus,
  Todo,
} from "../lib/types";

export function makeEvent(overrides: Partial<SeqEvent> = {}): SeqEvent {
  return {
    id: `evt-${overrides.seq ?? 0}`,
    type: "notification",
    ts: "2026-07-01T08:00:00.000Z",
    source: "core",
    correlation_id: null,
    payload: {},
    seq: 0,
    ...overrides,
  };
}

export function makeAgent(overrides: Partial<Agent> = {}): Agent {
  const status: AgentStatus = overrides.status ?? "idle";
  return {
    name: "HERMES",
    mode: "scheduled",
    permissions: [],
    enabled: true,
    status,
    last_run: null,
    conversational: false,
    ...overrides,
  };
}

/** Fabrique un événement `mail.triaged` (payload exact du contrat). */
export function makeTriaged(
  payload: {
    id: string;
    category?: string;
    priority?: number;
    summary?: string;
    subject?: string;
    sender?: string;
  },
  overrides: Partial<SeqEvent> = {},
): SeqEvent {
  return makeEvent({
    type: "mail.triaged",
    source: "HERMES",
    payload: {
      category: "info",
      priority: 1,
      summary: "",
      subject: "",
      sender: "",
      ...payload,
    },
    ...overrides,
  });
}

const EMPTY_TASK_COUNTS: Record<TaskStatus, number> = {
  backlog: 0,
  in_progress: 0,
  review: 0,
  done: 0,
  blocked: 0,
  failed: 0,
};

/** Fabrique un projet Mission Control. */
export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: "proj-1",
    name: "Projet démo",
    goal: "Livrer la démo",
    created_ts: "2026-07-01T08:00:00.000Z",
    task_counts: { ...EMPTY_TASK_COUNTS, ...overrides.task_counts },
    ...overrides,
  };
}

/** Fabrique une tâche Mission Control. */
export function makeTask(overrides: Partial<Task> = {}): Task {
  const status: TaskStatus = overrides.status ?? "backlog";
  return {
    id: "task-1",
    project_id: "proj-1",
    title: "Tâche démo",
    description: "Description de la tâche",
    acceptance_criteria: [],
    status,
    report: "",
    diff: "",
    blocker: null,
    updated_ts: "2026-07-01T09:00:00.000Z",
    ...overrides,
  };
}

/** Fabrique un rapport de nuit Mission Control. */
export function makeNightReport(overrides: Partial<NightReport> = {}): NightReport {
  return {
    date: "2026-07-02",
    done: 0,
    blocked: 0,
    failed: 0,
    cost_usd: 0,
    dry_run: true,
    tasks: [],
    blockers: [],
    ...overrides,
  };
}

/** Fabrique un événement `voice.heard` (ECHO a entendu une commande). */
export function makeVoiceHeard(
  payload: { transcript?: string; wake?: boolean; command?: string },
  overrides: Partial<SeqEvent> = {},
): SeqEvent {
  return makeEvent({
    type: "voice.heard",
    source: "ECHO",
    payload: {
      transcript: payload.transcript ?? "",
      wake: payload.wake ?? true,
      command: payload.command ?? "",
    },
    ...overrides,
  });
}

/** Fabrique un événement `voice.spoke` (réponse parlée de JARVIS). */
export function makeVoiceSpoke(
  payload: { text?: string; intent?: string; routed_to?: string | null },
  overrides: Partial<SeqEvent> = {},
): SeqEvent {
  return makeEvent({
    type: "voice.spoke",
    source: "ECHO",
    payload: {
      text: payload.text ?? "",
      intent: payload.intent ?? "chat",
      routed_to: payload.routed_to ?? null,
    },
    ...overrides,
  });
}

/** Fabrique un brouillon (GET /api/inbox/drafts). */
export function makeDraft(overrides: Partial<import("../lib/types").Draft> = {}) {
  return {
    mail_id: "m1",
    sender: "a@x.com",
    subject: "Sujet",
    body: "Bonjour,\n\nMerci pour votre message.",
    created_ts: "2026-07-01T08:00:00.000Z",
    ...overrides,
  };
}

/** Fabrique un événement `chat.message` (conversation multi-tours). */
export function makeChatMessage(
  payload: {
    conversationId: string;
    agent?: string;
    role?: "user" | "assistant";
    text?: string;
  },
  overrides: Partial<SeqEvent> = {},
): SeqEvent {
  return makeEvent({
    type: "chat.message",
    source: payload.agent ?? "JARVIS",
    payload: {
      conversation_id: payload.conversationId,
      agent: payload.agent ?? "JARVIS",
      role: payload.role ?? "assistant",
      text: payload.text ?? "",
    },
    ...overrides,
  });
}

/** Fabrique un élément d'agenda (miroir de TodoDTO). */
export function makeTodo(overrides: Partial<Todo> = {}): Todo {
  return {
    id: "todo-1",
    kind: "task",
    title: "Acheter du café",
    date: "2026-07-08",
    time: null,
    notes: "",
    status: "pending",
    remind_lead_min: 0,
    reminded_ts: null,
    tags: [],
    proposal: "",
    updated_ts: "2026-07-08T09:00:00.000Z",
    ...overrides,
  };
}

/** Fabrique un événement d'agenda (todo.created / reminder.due / …). */
export function makeTodoEvent(
  type: string,
  payload: Record<string, unknown>,
  seq = 0,
): SeqEvent {
  return makeEvent({ type, source: "CHRONOS", payload, seq });
}

/** Fabrique un événement `briefing.ready` (sections optionnelles). */
export function makeBriefing(
  payload: {
    text?: string;
    sections?: Record<string, unknown>;
  } = {},
  overrides: Partial<SeqEvent> = {},
): SeqEvent {
  return makeEvent({
    type: "briefing.ready",
    source: "ORACLE",
    payload: {
      text: payload.text ?? "",
      sections: payload.sections ?? {},
    },
    ...overrides,
  });
}
