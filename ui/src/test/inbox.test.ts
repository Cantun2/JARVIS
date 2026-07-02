import { describe, expect, it } from "vitest";
import { categoryColor, selectInbox } from "../lib/inbox";
import { makeTriaged, makeEvent } from "./fixtures";

describe("selectInbox", () => {
  it("ne garde que les événements mail.triaged", () => {
    const events = [
      makeTriaged({ id: "m1", priority: 2 }, { seq: 3 }),
      makeEvent({ seq: 2, type: "agent.finished" }),
      makeEvent({ seq: 1, type: "notification" }),
    ];
    const inbox = selectInbox(events);
    expect(inbox).toHaveLength(1);
    expect(inbox[0]?.id).toBe("m1");
  });

  it("déduplique par id en gardant l'occurrence la plus récente (seq)", () => {
    const events = [
      makeTriaged({ id: "m1", priority: 5, category: "urgent" }, { seq: 10 }),
      makeTriaged({ id: "m1", priority: 1, category: "info" }, { seq: 2 }),
    ];
    const inbox = selectInbox(events);
    expect(inbox).toHaveLength(1);
    expect(inbox[0]?.priority).toBe(5);
    expect(inbox[0]?.category).toBe("urgent");
  });

  it("trie par priorité décroissante", () => {
    const events = [
      makeTriaged({ id: "low", priority: 1 }, { seq: 1 }),
      makeTriaged({ id: "high", priority: 9 }, { seq: 2 }),
      makeTriaged({ id: "mid", priority: 5 }, { seq: 3 }),
    ];
    const inbox = selectInbox(events);
    expect(inbox.map((i) => i.id)).toEqual(["high", "mid", "low"]);
  });

  it("extrait tous les champs du payload", () => {
    const events = [
      makeTriaged(
        {
          id: "m1",
          category: "action",
          priority: 3,
          summary: "résumé",
          subject: "sujet",
          sender: "alice@x.io",
        },
        { seq: 1 },
      ),
    ];
    expect(selectInbox(events)[0]).toEqual({
      id: "m1",
      category: "action",
      priority: 3,
      summary: "résumé",
      subject: "sujet",
      sender: "alice@x.io",
    });
  });
});

describe("categoryColor", () => {
  it("mappe chaque catégorie à sa couleur HUD", () => {
    expect(categoryColor("urgent")).toBe("red");
    expect(categoryColor("action")).toBe("amber");
    expect(categoryColor("info")).toBe("cyan");
    expect(categoryColor("newsletter")).toBe("gray");
    expect(categoryColor("spam")).toBe("gray");
    expect(categoryColor("inconnu")).toBe("gray");
  });
});
