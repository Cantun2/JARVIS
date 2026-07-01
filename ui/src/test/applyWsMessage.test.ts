import { describe, expect, it } from "vitest";
import {
  applyWsMessage,
  backoffDelay,
  initialStreamState,
  MAX_EVENTS,
  parseWsMessage,
} from "../lib/ws";
import type { WsEvent, WsSnapshot } from "../lib/types";
import { makeAgent, makeEvent } from "./fixtures";

describe("applyWsMessage", () => {
  it("applique le snapshot initial (agents + événements + latest_seq)", () => {
    const snapshot: WsSnapshot = {
      kind: "snapshot",
      agents: [makeAgent({ name: "HERMES", status: "idle" })],
      events: [makeEvent({ seq: 1 }), makeEvent({ seq: 2 })],
      latest_seq: 2,
    };

    const state = applyWsMessage(initialStreamState, snapshot);

    expect(state.agents).toHaveLength(1);
    expect(state.agents[0]?.name).toBe("HERMES");
    expect(state.events).toHaveLength(2);
    expect(state.latestSeq).toBe(2);
    // Le plus récent (seq le plus grand) en tête.
    expect(state.events[0]?.seq).toBe(2);
    expect(state.events[1]?.seq).toBe(1);
  });

  it("ajoute un événement au-dessus du flux et met à jour latestSeq", () => {
    const snapshot: WsSnapshot = {
      kind: "snapshot",
      agents: [],
      events: [makeEvent({ seq: 1 })],
      latest_seq: 1,
    };
    const afterSnap = applyWsMessage(initialStreamState, snapshot);

    const evtMsg: WsEvent = { kind: "event", event: makeEvent({ seq: 2, type: "wake_up" }) };
    const state = applyWsMessage(afterSnap, evtMsg);

    expect(state.events).toHaveLength(2);
    expect(state.events[0]?.seq).toBe(2);
    expect(state.events[0]?.type).toBe("wake_up");
    expect(state.latestSeq).toBe(2);
  });

  it("ne duplique pas les événements après reconnexion (snapshot rejoué)", () => {
    const snapshot: WsSnapshot = {
      kind: "snapshot",
      agents: [makeAgent()],
      events: [makeEvent({ seq: 1 }), makeEvent({ seq: 2 })],
      latest_seq: 2,
    };
    let state = applyWsMessage(initialStreamState, snapshot);
    // Un nouvel événement arrive.
    state = applyWsMessage(state, { kind: "event", event: makeEvent({ seq: 3 }) });
    expect(state.events).toHaveLength(3);

    // Reconnexion : le serveur renvoie un snapshot qui recouvre seq 1..3.
    const reconnectSnapshot: WsSnapshot = {
      kind: "snapshot",
      agents: [makeAgent()],
      events: [makeEvent({ seq: 2 }), makeEvent({ seq: 3 }), makeEvent({ seq: 4 })],
      latest_seq: 4,
    };
    state = applyWsMessage(state, reconnectSnapshot);

    // Aucun doublon : seqs uniques {1,2,3,4}.
    const seqs = state.events.map((e) => e.seq).sort((a, b) => a - b);
    expect(seqs).toEqual([1, 2, 3, 4]);
    expect(state.latestSeq).toBe(4);
  });

  it("ne fait jamais régresser latestSeq", () => {
    const snapshot: WsSnapshot = {
      kind: "snapshot",
      agents: [],
      events: [makeEvent({ seq: 10 })],
      latest_seq: 10,
    };
    let state = applyWsMessage(initialStreamState, snapshot);
    // Un snapshot plus ancien (latest_seq inférieur) ne doit pas rabaisser.
    state = applyWsMessage(state, {
      kind: "snapshot",
      agents: [],
      events: [makeEvent({ seq: 5 })],
      latest_seq: 5,
    });
    expect(state.latestSeq).toBe(10);
  });

  it("plafonne le flux à MAX_EVENTS en gardant les plus récents", () => {
    const many = Array.from({ length: MAX_EVENTS + 50 }, (_, i) =>
      makeEvent({ seq: i + 1 }),
    );
    const state = applyWsMessage(initialStreamState, {
      kind: "snapshot",
      agents: [],
      events: many,
      latest_seq: many.length,
    });
    expect(state.events).toHaveLength(MAX_EVENTS);
    // Le plus récent conservé est le seq max ; le plus ancien conservé n'est pas seq 1.
    expect(state.events[0]?.seq).toBe(many.length);
    expect(state.events.at(-1)?.seq).toBe(50 + 1);
  });

  it("est pur : ne mute pas l'état d'entrée", () => {
    const frozen = Object.freeze({
      ...initialStreamState,
      events: Object.freeze([]) as never,
    });
    const next = applyWsMessage(frozen, {
      kind: "event",
      event: makeEvent({ seq: 1 }),
    });
    expect(next).not.toBe(frozen);
    expect(frozen.events).toHaveLength(0);
  });
});

describe("parseWsMessage", () => {
  it("parse un message valide", () => {
    const raw = JSON.stringify({ kind: "event", event: makeEvent({ seq: 1 }) });
    expect(parseWsMessage(raw)?.kind).toBe("event");
  });

  it("retourne null sur JSON invalide ou kind inconnu", () => {
    expect(parseWsMessage("pas du json")).toBeNull();
    expect(parseWsMessage(JSON.stringify({ kind: "autre" }))).toBeNull();
  });
});

describe("backoffDelay", () => {
  it("croît avec les tentatives et reste plafonné", () => {
    const d0 = backoffDelay(0, 500, 15000);
    const d1 = backoffDelay(1, 500, 15000);
    expect(d0).toBeGreaterThanOrEqual(500);
    expect(d1).toBeGreaterThan(d0 - 1); // tendance croissante malgré le jitter
    expect(backoffDelay(20, 500, 15000)).toBeLessThanOrEqual(15000);
  });
});
