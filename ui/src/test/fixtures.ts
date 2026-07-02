// Fabriques d'objets factices pour les tests (miroir du contrat de câble).
import type { Agent, AgentStatus, SeqEvent } from "../lib/types";

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
