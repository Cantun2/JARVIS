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
