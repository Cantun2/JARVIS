import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatPanel from "../components/ChatPanel";
import { makeAgent, makeChatMessage } from "./fixtures";

vi.mock("../lib/api", () => ({
  postChat: vi.fn().mockResolvedValue({
    conversation_id: "c1",
    agent: "JARVIS",
    reply: "Bonjour.",
    turns: 1,
  }),
  getChatHistory: vi.fn().mockResolvedValue({
    conversation_id: "c1",
    agent: "JARVIS",
    messages: [],
  }),
}));

import { postChat } from "../lib/api";

const AGENTS = [
  makeAgent({ name: "JARVIS", conversational: true }),
  makeAgent({ name: "PHEME", conversational: true }),
  makeAgent({ name: "ATLAS", conversational: false }),
];

describe("ChatPanel", () => {
  it("liste uniquement les agents conversationnels et l'état de base", () => {
    render(<ChatPanel events={[]} agents={AGENTS} />);
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("chat-mic")).toBeDisabled();
    expect(screen.getByTestId("chat-agent-JARVIS")).toBeInTheDocument();
    expect(screen.getByTestId("chat-agent-PHEME")).toBeInTheDocument();
    // ATLAS n'est pas conversationnel : pas de bouton de sélection.
    expect(screen.queryByTestId("chat-agent-ATLAS")).toBeNull();
  });

  it("affiche une bulle optimiste + l'indicateur de saisie et appelle postChat", async () => {
    render(<ChatPanel events={[]} agents={AGENTS} agent="JARVIS" />);
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "Bonjour" } });
    fireEvent.click(screen.getByTestId("chat-send"));

    // Optimiste : la bulle utilisateur + l'indicateur apparaissent tout de suite.
    const user = screen
      .getAllByTestId("chat-message")
      .find((m) => m.getAttribute("data-role") === "user");
    expect(user).toBeTruthy();
    expect(user).toHaveTextContent("Bonjour");
    expect(screen.getByTestId("chat-typing")).toBeInTheDocument();

    await waitFor(() =>
      expect(postChat).toHaveBeenCalledWith("JARVIS", "Bonjour", undefined),
    );
  });

  it("rend la bulle assistant à l'arrivée de l'événement chat.message", async () => {
    const { rerender } = render(<ChatPanel events={[]} agents={AGENTS} agent="JARVIS" />);
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "Salut" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(postChat).toHaveBeenCalled());

    rerender(
      <ChatPanel
        events={[
          makeChatMessage(
            { conversationId: "c1", role: "assistant", text: "Bonjour." },
            { seq: 5, id: "a1" },
          ),
        ]}
        agents={AGENTS}
        agent="JARVIS"
      />,
    );

    await waitFor(() => {
      const assistant = screen
        .getAllByTestId("chat-message")
        .find((m) => m.getAttribute("data-role") === "assistant");
      expect(assistant).toHaveTextContent("Bonjour.");
    });
  });

  it("sélectionner un autre agent conversationnel change la cible", async () => {
    render(<ChatPanel events={[]} agents={AGENTS} agent="JARVIS" />);
    fireEvent.click(screen.getByTestId("chat-agent-PHEME"));
    expect(screen.getByTestId("chat-agent-PHEME")).toHaveAttribute("aria-pressed", "true");

    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "coucou" } });
    fireEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() =>
      expect(postChat).toHaveBeenCalledWith("PHEME", "coucou", undefined),
    );
  });
});
