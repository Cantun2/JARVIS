import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TodoPanel from "../components/TodoPanel";
import { makeTodo, makeTodoEvent } from "./fixtures";

// On mocke le client API : le composant est piloté par ses retours.
vi.mock("../lib/api", () => ({
  getTodos: vi.fn(),
  getTodosMonth: vi.fn(),
  createTodo: vi.fn(),
  updateTodo: vi.fn(),
  setTodoStatus: vi.fn(),
  deleteTodo: vi.fn(),
}));

import { createTodo, getTodos, getTodosMonth, setTodoStatus } from "../lib/api";

const mockGetTodos = vi.mocked(getTodos);
const mockGetTodosMonth = vi.mocked(getTodosMonth);
const mockCreateTodo = vi.mocked(createTodo);
const mockSetStatus = vi.mocked(setTodoStatus);

describe("TodoPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetTodos.mockResolvedValue([
      makeTodo({ id: "a", title: "Acheter du café" }),
      makeTodo({ id: "b", title: "Dentiste", kind: "appointment", time: "14:30" }),
    ]);
    mockGetTodosMonth.mockResolvedValue([]);
    mockCreateTodo.mockResolvedValue(makeTodo({ id: "c", title: "Réunion" }));
    mockSetStatus.mockResolvedValue(makeTodo({ id: "a", status: "done" }));
  });

  it("affiche les éléments du jour retournés par l'API", async () => {
    render(<TodoPanel events={[]} />);

    await waitFor(() => expect(screen.getAllByTestId("todo-item")).toHaveLength(2));
    expect(screen.getByText("Acheter du café")).toBeInTheDocument();
    expect(screen.getByText("Dentiste")).toBeInTheDocument();
    expect(screen.getByTestId("todo-time-badge")).toHaveTextContent("14:30");
  });

  it("soumettre le formulaire appelle createTodo", async () => {
    render(<TodoPanel events={[]} />);
    await waitFor(() => expect(mockGetTodos).toHaveBeenCalled());

    fireEvent.change(screen.getByTestId("todo-title"), { target: { value: "Réunion" } });
    fireEvent.submit(screen.getByTestId("todo-form"));

    await waitFor(() => expect(mockCreateTodo).toHaveBeenCalled());
    const body = mockCreateTodo.mock.calls[0]![0];
    expect(body.title).toBe("Réunion");
    expect(body.kind).toBe("task");
  });

  it("basculer le statut appelle setTodoStatus (pending -> done)", async () => {
    render(<TodoPanel events={[]} />);
    await waitFor(() => expect(screen.getAllByTestId("todo-item")).toHaveLength(2));

    const first = screen.getAllByTestId("todo-item")[0]!;
    fireEvent.click(within(first).getByTestId("todo-toggle"));

    await waitFor(() => expect(mockSetStatus).toHaveBeenCalledWith("a", "done"));
  });

  it("affiche la proposition CHRONOS d'un todo", async () => {
    mockGetTodos.mockResolvedValue([
      makeTodo({ id: "p", title: "Déjeuner", proposal: "Déplacer à 13h ?" }),
    ]);
    render(<TodoPanel events={[]} />);

    await waitFor(() => expect(screen.getByTestId("todo-proposal")).toBeInTheDocument());
    expect(screen.getByText(/Déplacer à 13h/)).toBeInTheDocument();
  });

  it("affiche la bannière sur un événement reminder.due", async () => {
    render(
      <TodoPanel
        events={[
          makeTodoEvent(
            "reminder.due",
            { id: "a", title: "Dentiste", date: "2026-07-08", time: "14:30" },
            7,
          ),
        ]}
      />,
    );

    await waitFor(() => expect(screen.getByTestId("reminder-banner")).toBeInTheDocument());
    expect(screen.getByTestId("reminder-banner")).toHaveTextContent("Dentiste");
  });
});
