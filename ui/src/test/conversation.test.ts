import { describe, expect, it } from "vitest";
import { selectChatMessages } from "../lib/conversation";
import { makeChatMessage, makeEvent } from "./fixtures";

describe("selectChatMessages", () => {
  it("trie par seq croissant (les événements arrivent les plus récents en tête)", () => {
    const events = [
      makeChatMessage({ conversationId: "c1", role: "assistant", text: "Bonjour !" }, { seq: 2, id: "a" }),
      makeChatMessage({ conversationId: "c1", role: "user", text: "Salut" }, { seq: 1, id: "u" }),
    ];
    const msgs = selectChatMessages(events, "c1");
    expect(msgs.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(msgs[0].text).toBe("Salut");
    expect(msgs[1].text).toBe("Bonjour !");
    expect(msgs[0].id).toBe("u");
  });

  it("ne garde que les messages de la conversation demandée", () => {
    const events = [
      makeChatMessage({ conversationId: "c1", role: "user", text: "un" }, { seq: 1 }),
      makeChatMessage({ conversationId: "c2", role: "user", text: "autre" }, { seq: 2 }),
      makeChatMessage({ conversationId: "c1", role: "assistant", text: "deux" }, { seq: 3 }),
    ];
    const msgs = selectChatMessages(events, "c1");
    expect(msgs.map((m) => m.text)).toEqual(["un", "deux"]);
  });

  it("ignore les événements non chat.message", () => {
    const events = [
      makeChatMessage({ conversationId: "c1", role: "user", text: "coucou" }, { seq: 2 }),
      makeEvent({ seq: 1, type: "notification" }),
    ];
    expect(selectChatMessages(events, "c1")).toHaveLength(1);
  });

  it("ignore les messages sans rôle", () => {
    const events = [
      makeChatMessage({ conversationId: "c1", role: "user", text: "" }, { seq: 1, payload: { conversation_id: "c1", agent: "JARVIS", text: "vide" } }),
    ];
    // payload sans champ role -> ignoré
    expect(selectChatMessages(events, "c1")).toHaveLength(0);
  });
});
