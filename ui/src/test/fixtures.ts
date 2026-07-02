// Fabriques d'objets factices pour les tests (miroir du contrat de câble).
import type {
  Agent,
  AgentStatus,
  NightReport,
  Project,
  SeqEvent,
  Task,
  TaskStatus,
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
