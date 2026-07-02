import { describe, expect, it } from "vitest";
import { selectBriefing } from "../lib/briefing";
import { makeBriefing, makeEvent } from "./fixtures";

describe("selectBriefing", () => {
  it("retourne null sans briefing", () => {
    expect(selectBriefing([makeEvent({ seq: 1, type: "notification" })])).toBeNull();
    expect(selectBriefing([])).toBeNull();
  });

  it("prend le dernier briefing.ready (plus grand seq)", () => {
    const events = [
      makeBriefing({ text: "vieux" }, { seq: 1 }),
      makeBriefing({ text: "récent" }, { seq: 5 }),
      makeBriefing({ text: "moyen" }, { seq: 3 }),
    ];
    expect(selectBriefing(events)?.text).toBe("récent");
  });

  it("gère des sections absentes de façon défensive", () => {
    const b = selectBriefing([makeBriefing({ text: "hello" }, { seq: 1 })]);
    expect(b?.text).toBe("hello");
    expect(b?.sections.mails_urgents).toBeUndefined();
    expect(b?.sections.night_report).toBeUndefined();
    expect(b?.sections.meteo).toBeUndefined();
  });

  it("parse les sections complètes dont night_report", () => {
    const events = [
      makeBriefing(
        {
          text: "briefing complet",
          sections: {
            mails_urgents: [{ sender: "boss@x.io", subject: "urgent" }],
            calendrier: [{ time: "09:00", title: "standup" }],
            meteo: "ensoleillé",
            night_report: {
              date: "2026-07-02",
              done: 3,
              blocked: 1,
              failed: 0,
              cost_usd: 1.23,
              tasks: [
                { title: "feat A", status: "done", branch: "feat/a" },
                { title: "fix B", status: "blocked", note: "attente review" },
              ],
              blockers: ["CI rouge"],
            },
          },
        },
        { seq: 1 },
      ),
    ];
    const b = selectBriefing(events);
    expect(b?.sections.mails_urgents).toHaveLength(1);
    expect(b?.sections.mails_urgents?.[0]?.sender).toBe("boss@x.io");
    expect(b?.sections.calendrier?.[0]?.time).toBe("09:00");
    expect(b?.sections.meteo).toBe("ensoleillé");
    const nr = b?.sections.night_report;
    expect(nr?.done).toBe(3);
    expect(nr?.blocked).toBe(1);
    expect(nr?.cost_usd).toBe(1.23);
    expect(nr?.tasks).toHaveLength(2);
    expect(nr?.tasks[0]?.branch).toBe("feat/a");
    expect(nr?.tasks[1]?.note).toBe("attente review");
    expect(nr?.blockers).toEqual(["CI rouge"]);
  });

  it("tolère un night_report partiel", () => {
    const b = selectBriefing([
      makeBriefing({ sections: { night_report: { date: "2026-07-02" } } }, { seq: 1 }),
    ]);
    const nr = b?.sections.night_report;
    expect(nr?.date).toBe("2026-07-02");
    expect(nr?.done).toBe(0);
    expect(nr?.tasks).toEqual([]);
    expect(nr?.blockers).toEqual([]);
  });
});
