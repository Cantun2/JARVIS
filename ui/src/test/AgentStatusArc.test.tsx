import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AgentStatusArc from "../components/AgentStatusArc";
import { agentColor, overlayAgentStatus } from "../lib/theme";
import { makeAgent, makeEvent } from "./fixtures";

describe("agentColor (mapping statut -> couleur)", () => {
  it("finished/idle -> vert", () => {
    expect(agentColor("finished", true)).toBe("green");
    expect(agentColor("idle", true)).toBe("green");
  });
  it("started/escalated -> ambre", () => {
    expect(agentColor("started", true)).toBe("amber");
    expect(agentColor("escalated", true)).toBe("amber");
  });
  it("failed -> rouge", () => {
    expect(agentColor("failed", true)).toBe("red");
  });
  it("désactivé -> gris, quel que soit le statut", () => {
    expect(agentColor("finished", false)).toBe("gray");
    expect(agentColor("started", false)).toBe("gray");
    expect(agentColor("failed", false)).toBe("gray");
  });
});

describe("AgentStatusArc", () => {
  it("rend une pastille par agent avec la bonne couleur", () => {
    const agents = [
      makeAgent({ name: "HERMES", status: "finished" }),
      makeAgent({ name: "VULCAN", status: "started" }),
      makeAgent({ name: "ORACLE", status: "failed" }),
      makeAgent({ name: "SENTINEL", enabled: false, status: "idle" }),
    ];
    render(<AgentStatusArc agents={agents} />);

    const dots = screen.getAllByTestId("agent-dot");
    expect(dots).toHaveLength(4);

    const byName = (name: string) =>
      dots.find((d) => d.getAttribute("data-agent") === name)!;

    expect(byName("HERMES")).toHaveAttribute("data-color", "green");
    expect(byName("VULCAN")).toHaveAttribute("data-color", "amber");
    expect(byName("ORACLE")).toHaveAttribute("data-color", "red");
    expect(byName("SENTINEL")).toHaveAttribute("data-color", "gray");
    expect(byName("SENTINEL")).toHaveAttribute("data-enabled", "false");
  });

  it("affiche le nom de chaque agent", () => {
    render(<AgentStatusArc agents={[makeAgent({ name: "DAEDALUS" })]} />);
    const arc = screen.getByTestId("agent-arc");
    expect(within(arc).getByText("DAEDALUS")).toBeInTheDocument();
  });

  it("état vide propre", () => {
    render(<AgentStatusArc agents={[]} />);
    expect(screen.queryByTestId("agent-arc")).toBeNull();
    expect(screen.getByText(/Aucun agent/i)).toBeInTheDocument();
  });

  it("superpose le statut issu des événements agent.* (le plus récent gagne)", () => {
    const agents = [makeAgent({ name: "VULCAN", status: "idle" })];
    // Événements triés du plus récent (seq 2) au plus ancien (seq 1).
    const events = [
      makeEvent({ seq: 2, type: "agent.failed", payload: { agent: "VULCAN" } }),
      makeEvent({ seq: 1, type: "agent.started", payload: { agent: "VULCAN" } }),
    ];
    render(<AgentStatusArc agents={agents} events={events} />);
    const dot = screen.getByTestId("agent-dot");
    expect(dot).toHaveAttribute("data-status", "failed");
    expect(dot).toHaveAttribute("data-color", "red");
  });
});

describe("overlayAgentStatus (fonction pure)", () => {
  it("met à jour le statut via payload.agent", () => {
    const out = overlayAgentStatus(
      [makeAgent({ name: "HERMES", status: "idle" })],
      [makeEvent({ seq: 5, type: "agent.finished", payload: { agent: "HERMES" } })],
    );
    expect(out[0]?.status).toBe("finished");
  });

  it("retombe sur source si payload n'a ni agent ni name", () => {
    const out = overlayAgentStatus(
      [makeAgent({ name: "ORACLE", status: "idle" })],
      [makeEvent({ seq: 5, type: "agent.started", source: "ORACLE" })],
    );
    expect(out[0]?.status).toBe("started");
  });

  it("n'écrase pas le statut d'un agent désactivé", () => {
    const out = overlayAgentStatus(
      [makeAgent({ name: "VULCAN", status: "idle", enabled: false })],
      [makeEvent({ seq: 5, type: "agent.started", payload: { agent: "VULCAN" } })],
    );
    expect(out[0]?.status).toBe("idle");
  });

  it("ignore les événements non-agent", () => {
    const agents = [makeAgent({ name: "HERMES", status: "idle" })];
    const out = overlayAgentStatus(agents, [
      makeEvent({ seq: 1, type: "system.health" }),
    ]);
    expect(out[0]?.status).toBe("idle");
  });
});
