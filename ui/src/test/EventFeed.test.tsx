import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EventFeed from "../components/EventFeed";
import { eventColor } from "../lib/theme";
import { makeEvent } from "./fixtures";

describe("EventFeed", () => {
  it("rend N événements, le plus récent en haut", () => {
    const events = [
      makeEvent({ seq: 3, type: "agent.finished" }),
      makeEvent({ seq: 2, type: "agent.started" }),
      makeEvent({ seq: 1, type: "agent.failed" }),
    ];
    render(<EventFeed events={events} />);

    const rows = screen.getAllByTestId("event-row");
    expect(rows).toHaveLength(3);
    // Ordre préservé : le premier rendu correspond au premier élément fourni.
    expect(rows[0]).toHaveAttribute("data-type", "agent.finished");
    expect(rows[2]).toHaveAttribute("data-type", "agent.failed");
    expect(screen.getByTestId("feed-count")).toHaveTextContent("3");
  });

  it("applique le code couleur par type d'événement", () => {
    const events = [
      makeEvent({ seq: 4, type: "agent.finished" }), // green
      makeEvent({ seq: 3, type: "agent.started" }), // amber
      makeEvent({ seq: 2, type: "agent.failed" }), // red
      makeEvent({ seq: 1, type: "system.health" }), // cyan
    ];
    render(<EventFeed events={events} />);

    const rows = screen.getAllByTestId("event-row");
    expect(rows[0]).toHaveAttribute("data-color", "green");
    expect(rows[1]).toHaveAttribute("data-color", "amber");
    expect(rows[2]).toHaveAttribute("data-color", "red");
    expect(rows[3]).toHaveAttribute("data-color", "cyan");

    // Cohérence avec la fonction pure de mapping.
    expect(eventColor("agent.finished")).toBe("green");
    expect(eventColor("agent.failed")).toBe("red");
  });

  it("affiche un état vide sans événements", () => {
    render(<EventFeed events={[]} />);
    expect(screen.queryByTestId("event-feed")).toBeNull();
    expect(screen.getByText(/En attente d'événements/i)).toBeInTheDocument();
  });

  it("plafonne l'affichage à 200 lignes", () => {
    const events = Array.from({ length: 250 }, (_, i) =>
      makeEvent({ seq: 250 - i, type: "notification" }),
    );
    render(<EventFeed events={events} />);
    expect(screen.getAllByTestId("event-row")).toHaveLength(200);
  });

  it("affiche l'heure (mono), la source et le badge de type", () => {
    const events = [
      makeEvent({
        seq: 1,
        type: "mail.triaged",
        source: "HERMES",
        payload: { summary: "3 mails urgents" },
      }),
    ];
    render(<EventFeed events={events} />);
    expect(screen.getByTestId("event-badge")).toHaveTextContent("mail.triaged");
    expect(screen.getByText("HERMES")).toBeInTheDocument();
    expect(screen.getByText("3 mails urgents")).toBeInTheDocument();
  });
});
