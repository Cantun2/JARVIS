import { describe, expect, it } from "vitest";
import { groupByStatus, taskStatusColor } from "../lib/mission";
import type { TaskStatus } from "../lib/types";
import { makeTask } from "./fixtures";

describe("taskStatusColor", () => {
  it("mappe chaque statut sur sa couleur HUD", () => {
    const expected: Record<TaskStatus, string> = {
      backlog: "gray",
      in_progress: "cyan",
      review: "amber",
      done: "green",
      blocked: "amber",
      failed: "red",
    };
    (Object.keys(expected) as TaskStatus[]).forEach((status) => {
      expect(taskStatusColor(status)).toBe(expected[status]);
    });
  });
});

describe("groupByStatus", () => {
  it("regroupe les tâches par statut avec toutes les clés présentes", () => {
    const tasks = [
      makeTask({ id: "a", status: "backlog" }),
      makeTask({ id: "b", status: "backlog" }),
      makeTask({ id: "c", status: "review" }),
      makeTask({ id: "d", status: "done" }),
      makeTask({ id: "e", status: "blocked" }),
    ];
    const groups = groupByStatus(tasks);

    expect(groups.backlog.map((t) => t.id)).toEqual(["a", "b"]);
    expect(groups.review.map((t) => t.id)).toEqual(["c"]);
    expect(groups.done.map((t) => t.id)).toEqual(["d"]);
    expect(groups.blocked.map((t) => t.id)).toEqual(["e"]);
    expect(groups.in_progress).toEqual([]);
    expect(groups.failed).toEqual([]);
  });

  it("retourne toutes les clés même sans tâches", () => {
    const groups = groupByStatus([]);
    expect(Object.keys(groups).sort()).toEqual(
      ["backlog", "blocked", "done", "failed", "in_progress", "review"].sort(),
    );
  });
});
