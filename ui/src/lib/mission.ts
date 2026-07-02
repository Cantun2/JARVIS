// Helpers purs de Mission Control (testables sans DOM).
import type { HudColor } from "./theme";
import type { Task, TaskStatus } from "./types";

/** Statuts affichés en colonnes du kanban (Blocked est traité à part). */
export const KANBAN_STATUSES: TaskStatus[] = [
  "backlog",
  "in_progress",
  "review",
  "done",
];

/** Libellés lisibles par statut. */
export const STATUS_LABEL: Record<TaskStatus, string> = {
  backlog: "Backlog",
  in_progress: "In Progress",
  review: "Review",
  done: "Done",
  blocked: "Blocked",
  failed: "Failed",
};

/**
 * Couleur HUD d'un statut de tâche. Fonction pure :
 * backlog→gray, in_progress→cyan, review→amber, done→green,
 * blocked→amber, failed→red.
 */
export function taskStatusColor(status: TaskStatus): HudColor {
  switch (status) {
    case "in_progress":
      return "cyan";
    case "review":
    case "blocked":
      return "amber";
    case "done":
      return "green";
    case "failed":
      return "red";
    case "backlog":
    default:
      return "gray";
  }
}

/** Regroupe les tâches par statut (toutes les clés présentes). Fonction pure. */
export function groupByStatus(tasks: Task[]): Record<TaskStatus, Task[]> {
  const groups: Record<TaskStatus, Task[]> = {
    backlog: [],
    in_progress: [],
    review: [],
    done: [],
    blocked: [],
    failed: [],
  };
  for (const task of tasks) {
    groups[task.status].push(task);
  }
  return groups;
}
