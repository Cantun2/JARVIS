// Helpers purs de l'Agenda (testables sans DOM). Miroir du style de mission.ts.
import type { Todo, TodoStatus } from "./types";

/**
 * Types d'événements qui déclenchent un refetch de l'Agenda (liveSignature).
 * Alignés sur le contrat de câble CHRONOS.
 */
export const LIVE_TODO_TYPES: Set<string> = new Set([
  "todo.created",
  "todo.updated",
  "reminder.due",
  "appointment.upcoming",
  "agent.proposal",
]);

/** Rang de tri par statut : pending avant done avant cancelled. */
const STATUS_RANK: Record<TodoStatus, number> = {
  pending: 0,
  done: 1,
  cancelled: 2,
};

/**
 * Trie les éléments d'agenda (aligné sur le backend) : d'abord par statut
 * (pending, done, cancelled), puis les éléments sans heure avant ceux avec
 * heure croissante. Fonction pure : ne mute pas l'entrée.
 */
export function sortTodos(todos: Todo[]): Todo[] {
  return [...todos].sort((a, b) => {
    const rank = STATUS_RANK[a.status] - STATUS_RANK[b.status];
    if (rank !== 0) return rank;
    if (a.time === null && b.time === null) return 0;
    if (a.time === null) return -1;
    if (b.time === null) return 1;
    return a.time.localeCompare(b.time);
  });
}

/**
 * Ensemble des dates (YYYY-MM-DD) ayant au moins un élément d'agenda — sert à
 * afficher les pastilles du calendrier. Fonction pure.
 */
export function daySet(monthTodos: Todo[]): Set<string> {
  const days = new Set<string>();
  for (const t of monthTodos) days.add(t.date);
  return days;
}
