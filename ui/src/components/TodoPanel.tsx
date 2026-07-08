import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Calendar from "./Calendar";
import {
  createTodo,
  deleteTodo,
  getTodos,
  getTodosMonth,
  setTodoStatus,
} from "../lib/api";
import { todayYmd } from "../lib/date";
import { daySet, LIVE_TODO_TYPES, sortTodos } from "../lib/todo";
import type { CreateTodo, SeqEvent, Todo, TodoKind } from "../lib/types";

interface Props {
  events: SeqEvent[];
}

const KIND_LABEL: Record<TodoKind, string> = {
  task: "Tâche",
  appointment: "Rendez-vous",
};

/** Découpe une clé "YYYY-MM-DD" en année/mois (1-12) numériques. */
function ymToParts(ymd: string): { year: number; month: number } {
  const [y, m] = ymd.split("-").map(Number);
  const now = new Date();
  return {
    year: y && Number.isFinite(y) ? y : now.getFullYear(),
    month: m && Number.isFinite(m) ? m : now.getMonth() + 1,
  };
}

/** Libellé lisible d'un jour (ex. « mardi 8 juillet »). */
function dayLabel(ymd: string): string {
  const { year, month } = ymToParts(ymd);
  const [, , dStr] = ymd.split("-");
  const day = Number(dStr) || 1;
  return new Date(year, month - 1, day).toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

/**
 * Agenda : calendrier mensuel + liste du jour sélectionné + formulaire de
 * création. Refetch REST sur changement de jour/mois et sur événements live
 * CHRONOS (même motif `liveSignature` que Mission Control). CHRONOS ne fait que
 * proposer : aucune proposition n'est appliquée automatiquement.
 */
export default function TodoPanel({ events }: Props): JSX.Element {
  const initial = todayYmd();
  const initialParts = ymToParts(initial);

  const [selected, setSelected] = useState<string>(initial);
  const [viewYear, setViewYear] = useState<number>(initialParts.year);
  const [viewMonth, setViewMonth] = useState<number>(initialParts.month);
  const [dayTodos, setDayTodos] = useState<Todo[]>([]);
  const [monthTodos, setMonthTodos] = useState<Todo[]>([]);

  const [title, setTitle] = useState<string>("");
  const [kind, setKind] = useState<TodoKind>("task");
  const [time, setTime] = useState<string>("");
  const [remindLead, setRemindLead] = useState<string>("");

  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hiddenProposals, setHiddenProposals] = useState<Set<string>>(new Set());
  const [dismissedBannerSeq, setDismissedBannerSeq] = useState<number>(0);

  const loadDay = useCallback(async (ymd: string): Promise<void> => {
    setDayTodos(await getTodos(ymd));
  }, []);

  const loadMonth = useCallback(async (y: number, m: number): Promise<void> => {
    setMonthTodos(await getTodosMonth(y, m));
  }, []);

  // Rechargement de la liste du jour quand la sélection change.
  useEffect(() => {
    loadDay(selected).catch((err) =>
      setError(err instanceof Error ? err.message : "Chargement du jour échoué"),
    );
  }, [selected, loadDay]);

  // Rechargement des pastilles quand le mois affiché change.
  useEffect(() => {
    loadMonth(viewYear, viewMonth).catch(() => {
      /* pastilles best-effort */
    });
  }, [viewYear, viewMonth, loadMonth]);

  // Signature des événements live pertinents (plus grand seq).
  const liveSignature = useMemo(() => {
    let sig = 0;
    for (const ev of events) {
      if (!LIVE_TODO_TYPES.has(ev.type)) continue;
      if (ev.seq > sig) sig = ev.seq;
    }
    return sig;
  }, [events]);

  // Refetch live : dès qu'un événement CHRONOS pertinent apparaît.
  useEffect(() => {
    if (liveSignature === 0) return;
    loadDay(selected).catch(() => {
      /* refetch best-effort */
    });
    loadMonth(viewYear, viewMonth).catch(() => {
      /* refetch best-effort */
    });
  }, [liveSignature, selected, viewYear, viewMonth, loadDay, loadMonth]);

  // Agent proposant, par id de todo (dernier vu = plus récent, flux trié).
  const proposalAgents = useMemo(() => {
    const map = new Map<string, string>();
    for (const ev of events) {
      if (ev.type !== "agent.proposal") continue;
      const id = typeof ev.payload.id === "string" ? ev.payload.id : "";
      const agent = typeof ev.payload.agent === "string" ? ev.payload.agent : "";
      if (id && agent && !map.has(id)) map.set(id, agent);
    }
    return map;
  }, [events]);

  // Événement de rappel / rendez-vous le plus récent (bannière).
  const bannerEvent = useMemo(() => {
    let best: SeqEvent | null = null;
    for (const ev of events) {
      if (ev.type !== "reminder.due" && ev.type !== "appointment.upcoming") continue;
      if (!best || ev.seq > best.seq) best = ev;
    }
    return best;
  }, [events]);

  const showBanner = bannerEvent !== null && bannerEvent.seq > dismissedBannerSeq;

  const marked = useMemo(() => daySet(monthTodos), [monthTodos]);
  const sorted = useMemo(() => sortTodos(dayTodos), [dayTodos]);

  async function run(key: string, fn: () => Promise<void>): Promise<void> {
    setBusy(key);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action échouée");
    } finally {
      setBusy(null);
    }
  }

  function selectDay(ymd: string): void {
    setSelected(ymd);
    const { year, month } = ymToParts(ymd);
    setViewYear(year);
    setViewMonth(month);
  }

  function prevMonth(): void {
    const m = viewMonth === 1 ? 12 : viewMonth - 1;
    setViewYear(viewMonth === 1 ? viewYear - 1 : viewYear);
    setViewMonth(m);
  }

  function nextMonth(): void {
    const m = viewMonth === 12 ? 1 : viewMonth + 1;
    setViewYear(viewMonth === 12 ? viewYear + 1 : viewYear);
    setViewMonth(m);
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) return;
    await run("create", async () => {
      const body: CreateTodo = { title: trimmed, date: selected, kind };
      if (time) body.time = time;
      const lead = Number(remindLead);
      if (remindLead !== "" && Number.isFinite(lead)) body.remind_lead_min = lead;
      await createTodo(body);
      setTitle("");
      setTime("");
      setRemindLead("");
      await loadDay(selected);
      await loadMonth(viewYear, viewMonth);
    });
  }

  async function handleToggle(todo: Todo): Promise<void> {
    const next = todo.status === "done" ? "pending" : "done";
    await run(`toggle-${todo.id}`, async () => {
      await setTodoStatus(todo.id, next);
      await loadDay(selected);
      await loadMonth(viewYear, viewMonth);
    });
  }

  async function handleDelete(id: string): Promise<void> {
    await run(`delete-${id}`, async () => {
      await deleteTodo(id);
      await loadDay(selected);
      await loadMonth(viewYear, viewMonth);
    });
  }

  function hideProposal(id: string): void {
    setHiddenProposals((prev) => new Set(prev).add(id));
  }

  return (
    <section
      className="hud-panel flex min-h-0 flex-1 flex-col"
      aria-label="Agenda"
      data-testid="todo-panel"
    >
      <header className="flex items-center justify-between gap-3 border-b border-hud-border px-3 py-2">
        <h2 className="hud-label">Agenda</h2>
        <span className="text-[10px] tabular-nums text-hud-muted" data-testid="todo-count">
          {dayTodos.length}
        </span>
      </header>

      {showBanner && bannerEvent && (
        <div
          className="flex items-center justify-between gap-2 border-b border-hud-amber/30 bg-hud-amber/10 px-3 py-1.5 text-[11px] text-hud-amber"
          role="status"
          data-testid="reminder-banner"
        >
          <span>
            {bannerEvent.type === "reminder.due" ? "Rappel" : "Rendez-vous"} —{" "}
            {String(bannerEvent.payload.title ?? "")}
            {bannerEvent.payload.time ? ` à ${String(bannerEvent.payload.time)}` : ""}
          </span>
          <button
            type="button"
            onClick={() => setDismissedBannerSeq(bannerEvent.seq)}
            className="rounded border border-hud-amber/40 px-1.5 py-0.5 text-[10px] uppercase tracking-wide transition hover:bg-hud-amber/20"
            data-testid="reminder-dismiss"
          >
            Fermer
          </button>
        </div>
      )}

      {error && (
        <div
          className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red"
          role="alert"
          data-testid="todo-error"
        >
          {error}
        </div>
      )}

      <motion.div
        className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto p-3 lg:grid-cols-[minmax(0,20rem)_1fr]"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <div className="space-y-3">
          <Calendar
            year={viewYear}
            month={viewMonth}
            selected={selected}
            marked={marked}
            onSelectDay={selectDay}
            onPrevMonth={prevMonth}
            onNextMonth={nextMonth}
          />

          <form
            onSubmit={handleSubmit}
            className="hud-panel space-y-2 p-3"
            data-testid="todo-form"
          >
            <div className="hud-label">Nouvel élément</div>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Titre…"
              required
              className="w-full rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text placeholder:text-hud-muted"
              data-testid="todo-title"
              aria-label="Titre"
            />
            <div className="flex gap-2">
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as TodoKind)}
                className="flex-1 rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text"
                data-testid="todo-kind"
                aria-label="Type"
              >
                <option value="task">Tâche</option>
                <option value="appointment">Rendez-vous</option>
              </select>
              <input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="w-28 rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text"
                data-testid="todo-time"
                aria-label="Heure"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                value={remindLead}
                onChange={(e) => setRemindLead(e.target.value)}
                placeholder="Rappel (min avant)"
                className="flex-1 rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text placeholder:text-hud-muted"
                data-testid="todo-remind"
                aria-label="Rappel en minutes"
              />
              <button
                type="submit"
                disabled={busy !== null || title.trim() === ""}
                className="rounded border border-hud-cyan/40 bg-hud-cyan/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-cyan transition hover:bg-hud-cyan/20 disabled:opacity-50"
                data-testid="todo-submit"
              >
                {busy === "create" ? "Ajout…" : "Ajouter"}
              </button>
            </div>
          </form>
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex items-baseline gap-2">
            <h3 className="text-sm font-medium capitalize text-hud-text" data-testid="todo-day-label">
              {dayLabel(selected)}
            </h3>
          </div>

          {sorted.length === 0 ? (
            <p
              className="rounded-lg border border-hud-border bg-hud-panel/40 p-6 text-center text-xs text-hud-muted"
              data-testid="todo-empty"
            >
              Aucun élément ce jour
            </p>
          ) : (
            <ul className="space-y-2" data-testid="todo-list">
              {sorted.map((todo) => (
                <TodoRow
                  key={todo.id}
                  todo={todo}
                  busy={busy}
                  agent={proposalAgents.get(todo.id) ?? "CHRONOS"}
                  proposalHidden={hiddenProposals.has(todo.id)}
                  onToggle={handleToggle}
                  onDelete={handleDelete}
                  onHideProposal={hideProposal}
                />
              ))}
            </ul>
          )}
        </div>
      </motion.div>
    </section>
  );
}

function TodoRow({
  todo,
  busy,
  agent,
  proposalHidden,
  onToggle,
  onDelete,
  onHideProposal,
}: {
  todo: Todo;
  busy: string | null;
  agent: string;
  proposalHidden: boolean;
  onToggle: (todo: Todo) => void;
  onDelete: (id: string) => void;
  onHideProposal: (id: string) => void;
}): JSX.Element {
  const done = todo.status === "done";
  const showProposal = todo.proposal !== "" && !proposalHidden;
  return (
    <li
      className="rounded-md border border-hud-border bg-hud-bg/60 p-2"
      data-testid="todo-item"
      data-status={todo.status}
      data-kind={todo.kind}
    >
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onToggle(todo)}
          disabled={busy !== null}
          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] transition disabled:opacity-50 ${
            done
              ? "border-hud-green bg-hud-green/20 text-hud-green"
              : "border-hud-border text-transparent hover:border-hud-cyan"
          }`}
          data-testid="todo-toggle"
          aria-label={done ? "Marquer à faire" : "Marquer fait"}
          aria-pressed={done}
        >
          ✓
        </button>

        <span
          className={`shrink-0 rounded border px-1 py-0.5 text-[9px] uppercase tracking-wide ${
            todo.kind === "appointment"
              ? "border-hud-cyan/40 bg-hud-cyan/10 text-hud-cyan"
              : "border-hud-gray/40 bg-hud-gray/10 text-hud-gray"
          }`}
        >
          {KIND_LABEL[todo.kind]}
        </span>

        <span
          className={`min-w-0 flex-1 truncate text-xs ${
            done ? "text-hud-muted line-through" : "text-hud-text"
          }`}
        >
          {todo.title}
        </span>

        {todo.time && (
          <span
            className="shrink-0 rounded border border-hud-border px-1 py-0.5 text-[10px] tabular-nums text-hud-muted"
            data-testid="todo-time-badge"
          >
            {todo.time}
          </span>
        )}

        <button
          type="button"
          onClick={() => onDelete(todo.id)}
          disabled={busy !== null}
          className="shrink-0 rounded border border-hud-red/40 px-1.5 py-0.5 text-[10px] text-hud-red transition hover:bg-hud-red/10 disabled:opacity-50"
          data-testid="todo-delete"
          aria-label="Supprimer"
        >
          ✕
        </button>
      </div>

      {showProposal && (
        <div
          className="mt-2 flex items-start justify-between gap-2 rounded border border-hud-amber/30 bg-hud-amber/5 px-2 py-1.5"
          data-testid="todo-proposal"
        >
          <div className="min-w-0">
            <span className="hud-label text-hud-amber" data-testid="todo-proposal-agent">
              {agent}
            </span>
            <p className="mt-0.5 text-[11px] text-hud-text">{todo.proposal}</p>
          </div>
          <button
            type="button"
            onClick={() => onHideProposal(todo.id)}
            className="shrink-0 rounded border border-hud-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-hud-muted transition hover:text-hud-text"
            data-testid="todo-proposal-dismiss"
          >
            Ignorer
          </button>
        </div>
      )}
    </li>
  );
}
