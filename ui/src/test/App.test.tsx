import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "../App";
import { makeTriaged } from "./fixtures";

// On mocke le hook de flux : les vues sont dérivées de `events`, on n'a pas
// besoin d'un vrai WebSocket pour tester la navigation par onglets.
vi.mock("../lib/ws", () => ({
  useEventStream: () => ({
    events: [makeTriaged({ id: "m1", category: "urgent", subject: "prod down" }, { seq: 1 })],
    agents: [],
    health: null,
    connected: false,
  }),
}));

describe("App — navigation par onglets", () => {
  it("affiche le Dashboard par défaut", () => {
    render(<App />);
    expect(screen.getByTestId("tab-dashboard")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Flux d'événements")).toBeInTheDocument();
  });

  it("cliquer l'onglet Inbox affiche l'InboxPanel", () => {
    render(<App />);

    fireEvent.click(screen.getByTestId("tab-inbox"));

    expect(screen.getByTestId("tab-inbox")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("inbox-panel")).toBeInTheDocument();
    expect(screen.getByText("prod down")).toBeInTheDocument();
    expect(screen.queryByLabelText("Flux d'événements")).toBeNull();
  });

  it("cliquer l'onglet Briefing affiche le BriefingPanel", () => {
    render(<App />);

    fireEvent.click(screen.getByTestId("tab-briefing"));

    expect(screen.getByTestId("tab-briefing")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("briefing-panel")).toBeInTheDocument();
  });
});
