import { describe, expect, it } from "vitest";
import { selectChat } from "../lib/chat";
import { makeVoiceHeard, makeVoiceSpoke } from "./fixtures";

describe("selectChat", () => {
  it("apparie heard/spoke dans l'ordre chronologique (par seq croissant)", () => {
    // Les événements arrivent les plus récents en tête (comme le flux WS).
    const events = [
      makeVoiceSpoke({ text: "Bonjour.", intent: "briefing", routed_to: "ORACLE" }, { seq: 2, id: "s" }),
      makeVoiceHeard({ command: "fais le briefing", wake: true }, { seq: 1, id: "h" }),
    ];
    const msgs = selectChat(events);
    expect(msgs.map((m) => m.role)).toEqual(["user", "jarvis"]);
    expect(msgs[0].text).toBe("fais le briefing");
    expect(msgs[1].text).toBe("Bonjour.");
    expect(msgs[1].routedTo).toBe("ORACLE");
    expect(msgs[1].spoke).toBe(true);
  });

  it("ignore les 'heard' sans wake-word", () => {
    const events = [
      makeVoiceHeard({ command: "", transcript: "quelle heure", wake: false }, { seq: 1 }),
    ];
    expect(selectChat(events)).toHaveLength(0);
  });

  it("utilise transcript en repli si command est vide", () => {
    const events = [
      makeVoiceHeard({ command: "", transcript: "Jarvis salut", wake: true }, { seq: 1 }),
    ];
    expect(selectChat(events)[0].text).toBe("Jarvis salut");
  });

  it("ignore les événements non-voix", () => {
    const events = [makeVoiceSpoke({ text: "" }, { seq: 1 })];
    expect(selectChat(events)).toHaveLength(0); // texte vide -> ignoré
  });
});
