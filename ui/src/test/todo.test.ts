import { describe, expect, it } from "vitest";
import { daySet, LIVE_TODO_TYPES, sortTodos } from "../lib/todo";
import { makeTodo } from "./fixtures";

describe("LIVE_TODO_TYPES", () => {
  it("contient les 5 types d'événements agenda", () => {
    for (const t of [
      "todo.created",
      "todo.updated",
      "reminder.due",
      "appointment.upcoming",
      "agent.proposal",
    ]) {
      expect(LIVE_TODO_TYPES.has(t)).toBe(true);
    }
  });

  it("ignore les types non pertinents", () => {
    expect(LIVE_TODO_TYPES.has("mail.triaged")).toBe(false);
    expect(LIVE_TODO_TYPES.has("task.transitioned")).toBe(false);
  });
});

describe("sortTodos", () => {
  it("trie pending avant done, puis untimed avant heures croissantes", () => {
    const todos = [
      makeTodo({ id: "done-early", status: "done", time: "08:00" }),
      makeTodo({ id: "t10", status: "pending", time: "10:00" }),
      makeTodo({ id: "untimed", status: "pending", time: null }),
      makeTodo({ id: "t09", status: "pending", time: "09:00" }),
    ];
    const sorted = sortTodos(todos);
    expect(sorted.map((t) => t.id)).toEqual(["untimed", "t09", "t10", "done-early"]);
  });

  it("place cancelled en dernier", () => {
    const todos = [
      makeTodo({ id: "cancel", status: "cancelled" }),
      makeTodo({ id: "pend", status: "pending" }),
      makeTodo({ id: "done", status: "done" }),
    ];
    expect(sortTodos(todos).map((t) => t.id)).toEqual(["pend", "done", "cancel"]);
  });

  it("ne mute pas le tableau d'entrée", () => {
    const todos = [
      makeTodo({ id: "b", time: "10:00" }),
      makeTodo({ id: "a", time: null }),
    ];
    sortTodos(todos);
    expect(todos.map((t) => t.id)).toEqual(["b", "a"]);
  });
});

describe("daySet", () => {
  it("collecte les dates ayant au moins un élément", () => {
    const set = daySet([
      makeTodo({ id: "1", date: "2026-07-01" }),
      makeTodo({ id: "2", date: "2026-07-01" }),
      makeTodo({ id: "3", date: "2026-07-05" }),
    ]);
    expect(set.size).toBe(2);
    expect(set.has("2026-07-01")).toBe(true);
    expect(set.has("2026-07-05")).toBe(true);
    expect(set.has("2026-07-02")).toBe(false);
  });

  it("renvoie un ensemble vide sans todo", () => {
    expect(daySet([]).size).toBe(0);
  });
});
