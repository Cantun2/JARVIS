import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import InboxPanel from "../components/InboxPanel";
import { categoryColor } from "../lib/inbox";
import { makeTriaged } from "./fixtures";

describe("InboxPanel", () => {
  it("rend N items triés par priorité avec badges colorés par catégorie", () => {
    const events = [
      makeTriaged({ id: "u", category: "urgent", priority: 9, subject: "prod down" }, { seq: 3 }),
      makeTriaged({ id: "a", category: "action", priority: 5, subject: "à valider" }, { seq: 2 }),
      makeTriaged({ id: "n", category: "newsletter", priority: 1, subject: "hebdo" }, { seq: 1 }),
    ];
    render(<InboxPanel events={events} />);

    const rows = screen.getAllByTestId("inbox-row");
    expect(rows).toHaveLength(3);
    // Tri par priorité décroissante.
    expect(rows[0]).toHaveAttribute("data-category", "urgent");
    expect(rows[1]).toHaveAttribute("data-category", "action");
    expect(rows[2]).toHaveAttribute("data-category", "newsletter");
    // Couleur dérivée exclusivement de categoryColor.
    expect(rows[0]).toHaveAttribute("data-color", categoryColor("urgent"));
    expect(rows[0]).toHaveAttribute("data-color", "red");
    expect(rows[1]).toHaveAttribute("data-color", "amber");

    expect(screen.getByTestId("inbox-count")).toHaveTextContent("3");
    expect(screen.getByText("prod down")).toBeInTheDocument();
  });

  it("affiche l'état vide et le bouton de tri", () => {
    render(<InboxPanel events={[]} />);
    expect(screen.queryByTestId("inbox-list")).toBeNull();
    expect(screen.getByTestId("inbox-empty")).toHaveTextContent(/Aucun mail trié — lance HERMES/i);
    expect(screen.getByTestId("inbox-refresh")).toBeInTheDocument();
  });
});
