import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatPanel from "../components/ChatPanel";
import { makeVoiceHeard, makeVoiceSpoke } from "./fixtures";

vi.mock("../lib/api", () => ({
  sayToEcho: vi.fn().mockResolvedValue({
    heard: "Jarvis, le briefing",
    wake_detected: true,
    intent: "briefing",
    routed_to: "ORACLE",
    response: "Bonjour.",
    spoke: true,
  }),
}));

import { sayToEcho } from "../lib/api";

describe("ChatPanel", () => {
  it("affiche l'état vide, le champ commande et le bouton micro", () => {
    render(<ChatPanel events={[]} />);
    expect(screen.getByTestId("chat-empty")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("chat-mic")).toBeDisabled();
  });

  it("rend le transcript avec l'agent routé et l'indicateur parlé", () => {
    const events = [
      makeVoiceHeard({ command: "fais le briefing", wake: true }, { seq: 1, id: "h" }),
      makeVoiceSpoke({ text: "Bonjour.", routed_to: "ORACLE" }, { seq: 2, id: "s" }),
    ];
    render(<ChatPanel events={events} />);
    const msgs = screen.getAllByTestId("chat-message");
    expect(msgs).toHaveLength(2);
    expect(msgs[0]).toHaveAttribute("data-role", "user");
    expect(msgs[1]).toHaveAttribute("data-role", "jarvis");
    expect(screen.getByTestId("chat-routed")).toHaveTextContent("ORACLE");
    expect(screen.getByTestId("chat-spoken")).toHaveTextContent("parlé");
  });

  it("envoie la commande à ECHO au submit", async () => {
    render(<ChatPanel events={[]} />);
    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "Jarvis, le briefing" },
    });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(sayToEcho).toHaveBeenCalledWith("Jarvis, le briefing"));
  });
});
