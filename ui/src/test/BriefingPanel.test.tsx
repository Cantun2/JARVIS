import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BriefingPanel from "../components/BriefingPanel";
import { makeBriefing } from "./fixtures";

describe("BriefingPanel", () => {
  it("affiche l'état vide et les boutons de déclenchement", () => {
    render(<BriefingPanel events={[]} />);
    expect(screen.getByTestId("briefing-empty")).toHaveTextContent(/Pas encore de briefing/i);
    expect(screen.getByTestId("briefing-generate")).toBeInTheDocument();
    expect(screen.getByTestId("briefing-wake")).toBeInTheDocument();
  });

  it("rend le texte et les sections dont le night report", () => {
    const events = [
      makeBriefing(
        {
          text: "Bonjour, voici ton briefing.",
          sections: {
            mails_urgents: [{ sender: "boss@x.io", subject: "budget" }],
            calendrier: [{ time: "09:00", title: "standup" }],
            meteo: "22°C ensoleillé",
            night_report: {
              date: "2026-07-02",
              done: 4,
              blocked: 2,
              failed: 1,
              cost_usd: 2.5,
              tasks: [
                { title: "feat login", status: "done", branch: "feat/login" },
                { title: "fix flaky", status: "blocked", note: "review requise" },
              ],
              blockers: ["accès API manquant"],
            },
          },
        },
        { seq: 1 },
      ),
    ];
    render(<BriefingPanel events={events} />);

    expect(screen.getByTestId("briefing-text")).toHaveTextContent("Bonjour, voici ton briefing.");
    expect(screen.getByTestId("briefing-section-mails")).toHaveTextContent("boss@x.io");
    expect(screen.getByTestId("briefing-section-calendrier")).toHaveTextContent("standup");
    expect(screen.getByTestId("briefing-section-meteo")).toHaveTextContent("22°C ensoleillé");

    const night = screen.getByTestId("briefing-section-night");
    expect(night).toBeInTheDocument();
    expect(screen.getByTestId("night-done")).toHaveTextContent("4");
    expect(screen.getByTestId("night-blocked")).toHaveTextContent("2");
    expect(screen.getByTestId("night-failed")).toHaveTextContent("1");
    expect(screen.getAllByTestId("night-task")).toHaveLength(2);
    expect(screen.getByTestId("night-blockers")).toHaveTextContent("accès API manquant");
    expect(screen.getByText("feat login")).toBeInTheDocument();
  });

  it("n'affiche que les sections présentes", () => {
    render(<BriefingPanel events={[makeBriefing({ text: "court" }, { seq: 1 })]} />);
    expect(screen.getByTestId("briefing-text")).toHaveTextContent("court");
    expect(screen.queryByTestId("briefing-section-night")).toBeNull();
    expect(screen.queryByTestId("briefing-section-mails")).toBeNull();
  });
});
