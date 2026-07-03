import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import InboxRow from "../components/InboxRow";
import type { InboxItem } from "../lib/inbox";

function item(overrides: Partial<InboxItem> = {}): InboxItem {
  return {
    id: "m1",
    category: "action",
    priority: 70,
    summary: "résumé",
    subject: "À valider",
    sender: "boss@x.com",
    draft: null,
    corrected: false,
    ...overrides,
  };
}

describe("InboxRow (Inbox v2)", () => {
  it("déplie le brouillon quand il existe", () => {
    render(<InboxRow item={item({ draft: "Bonjour,\n\nMerci." })} />);
    expect(screen.queryByTestId("inbox-draft")).toBeNull();
    fireEvent.click(screen.getByTestId("inbox-draft-toggle"));
    expect(screen.getByTestId("inbox-draft")).toHaveTextContent("Merci.");
  });

  it("n'affiche pas de bouton brouillon sans brouillon", () => {
    render(<InboxRow item={item({ draft: null })} />);
    expect(screen.queryByTestId("inbox-draft-toggle")).toBeNull();
  });

  it("appelle onReclassify au changement de catégorie", () => {
    const onReclassify = vi.fn();
    render(<InboxRow item={item()} onReclassify={onReclassify} />);
    fireEvent.change(screen.getByTestId("inbox-reclassify"), {
      target: { value: "spam" },
    });
    expect(onReclassify).toHaveBeenCalledWith("m1", "spam");
  });

  it("montre le badge corrigé", () => {
    render(<InboxRow item={item({ corrected: true })} />);
    expect(screen.getByTestId("inbox-corrected")).toBeInTheDocument();
  });
});
