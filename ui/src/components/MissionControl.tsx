import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  createProject,
  getNightReport,
  getProjects,
  getProjectTasks,
  runNight,
  transitionTask,
} from "../lib/api";
import {
  groupByStatus,
  KANBAN_STATUSES,
  STATUS_LABEL,
  taskStatusColor,
} from "../lib/mission";
import { HUD_BADGE_CLASS } from "../lib/theme";
import type {
  NightReport,
  Project,
  SeqEvent,
  Task,
  TaskAction,
  TaskStatus,
} from "../lib/types";

interface Props {
  events: SeqEvent[];
}

/** Types d'événements qui déclenchent un refetch de Mission Control. */
const LIVE_TYPES = new Set([
  "backlog.ready",
  "task.transitioned",
  "night.report_ready",
]);

/** Actions autorisées selon le statut courant d'une tâche. */
function actionsFor(status: TaskStatus): TaskAction[] {
  switch (status) {
    case "review":
      return ["approve", "reject"];
    case "failed":
    case "blocked":
      return ["retry"];
    default:
      return [];
  }
}

const ACTION_LABEL: Record<TaskAction, string> = {
  approve: "Approve",
  reject: "Reject",
  retry: "Retry",
};

const ACTION_COLOR: Record<TaskAction, "green" | "red" | "amber"> = {
  approve: "green",
  reject: "red",
  retry: "amber",
};

/**
 * Mission Control : sélection de projet, génération de backlog, kanban des
 * tâches (+ file Blocked), transitions, lancement de nuit dry-run et rapport.
 * Refetch simple sur événements live du projet courant.
 */
export default function MissionControl({ events }: Props): JSX.Element {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [report, setReport] = useState<NightReport | null>(null);
  const [goal, setGoal] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async (): Promise<Project[]> => {
    const list = await getProjects();
    setProjects(list);
    return list;
  }, []);

  const loadTasks = useCallback(async (pid: string): Promise<void> => {
    if (!pid) {
      setTasks([]);
      return;
    }
    setTasks(await getProjectTasks(pid));
  }, []);

  const loadReport = useCallback(async (): Promise<void> => {
    setReport(await getNightReport());
  }, []);

  // Chargement initial des projets : sélectionne le premier par défaut.
  useEffect(() => {
    loadProjects()
      .then((list) => {
        const first = list[0];
        if (first) setProjectId((cur) => cur || first.id);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Chargement des projets échoué"),
      );
  }, [loadProjects]);

  // Rechargement des tâches + rapport quand le projet change.
  useEffect(() => {
    if (!projectId) return;
    loadTasks(projectId).catch((err) =>
      setError(err instanceof Error ? err.message : "Chargement des tâches échoué"),
    );
    loadReport().catch(() => {
      /* rapport optionnel */
    });
  }, [projectId, loadTasks, loadReport]);

  // Signature des événements live pertinents pour le projet courant.
  const liveSignature = useMemo(() => {
    if (!projectId) return 0;
    let sig = 0;
    for (const ev of events) {
      if (!LIVE_TYPES.has(ev.type)) continue;
      const pid = ev.payload.project_id;
      if (typeof pid === "string" && pid !== projectId) continue;
      if (ev.seq > sig) sig = ev.seq;
    }
    return sig;
  }, [events, projectId]);

  // Refetch live : dès qu'un event pertinent (seq plus grand) apparaît.
  useEffect(() => {
    if (!projectId || liveSignature === 0) return;
    loadTasks(projectId).catch(() => {
      /* refetch best-effort */
    });
    loadReport().catch(() => {
      /* refetch best-effort */
    });
  }, [liveSignature, projectId, loadTasks, loadReport]);

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

  async function handleGenerate(): Promise<void> {
    const trimmed = goal.trim();
    if (!trimmed) return;
    await run("generate", async () => {
      const { project } = await createProject(trimmed);
      setGoal("");
      await loadProjects();
      setProjectId(project.id);
      await loadTasks(project.id);
    });
  }

  async function handleNight(): Promise<void> {
    if (!projectId) return;
    await run("night", async () => {
      const rep = await runNight(projectId);
      setReport(rep);
    });
  }

  async function handleTransition(taskId: string, action: TaskAction): Promise<void> {
    await run(`task-${taskId}-${action}`, async () => {
      await transitionTask(taskId, action);
      await loadTasks(projectId);
    });
  }

  const groups = useMemo(() => groupByStatus(tasks), [tasks]);

  return (
    <section
      className="hud-panel flex min-h-0 flex-1 flex-col"
      aria-label="Mission Control"
      data-testid="mission-panel"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-hud-border px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="hud-label">Mission Control</h2>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            disabled={projects.length === 0}
            className="rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text disabled:opacity-50"
            data-testid="project-select"
            aria-label="Projet"
          >
            {projects.length === 0 && <option value="">Aucun projet</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void handleNight()}
            disabled={busy !== null || !projectId}
            className="rounded border border-hud-amber/40 bg-hud-amber/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-amber transition hover:bg-hud-amber/20 disabled:opacity-50"
            data-testid="night-run"
          >
            {busy === "night" ? "Nuit…" : "Lancer la nuit (dry-run)"}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Objectif du projet…"
            className="w-56 rounded border border-hud-border bg-hud-panel px-2 py-1 text-xs text-hud-text placeholder:text-hud-muted"
            data-testid="goal-input"
            aria-label="Objectif du projet"
          />
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={busy !== null || goal.trim() === ""}
            className="rounded border border-hud-cyan/40 bg-hud-cyan/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-cyan transition hover:bg-hud-cyan/20 disabled:opacity-50"
            data-testid="backlog-generate"
          >
            {busy === "generate" ? "Génération…" : "Générer un backlog"}
          </button>
        </div>
      </header>

      {error && (
        <div
          className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red"
          role="alert"
          data-testid="mission-error"
        >
          {error}
        </div>
      )}

      <motion.div
        className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" data-testid="kanban">
          {KANBAN_STATUSES.map((status) => (
            <Column
              key={status}
              status={status}
              tasks={groups[status]}
              busy={busy}
              onTransition={handleTransition}
            />
          ))}
        </div>

        <Column
          status="blocked"
          tasks={groups.blocked}
          busy={busy}
          onTransition={handleTransition}
          testid="blocked-queue"
        />

        {groups.failed.length > 0 && (
          <Column
            status="failed"
            tasks={groups.failed}
            busy={busy}
            onTransition={handleTransition}
            testid="failed-queue"
          />
        )}

        <NightReportBlock report={report} />
      </motion.div>
    </section>
  );
}

function Column({
  status,
  tasks,
  busy,
  onTransition,
  testid,
}: {
  status: TaskStatus;
  tasks: Task[];
  busy: string | null;
  onTransition: (taskId: string, action: TaskAction) => void;
  testid?: string;
}): JSX.Element {
  const color = taskStatusColor(status);
  return (
    <div
      className="flex min-w-0 flex-col rounded-lg border border-hud-border bg-hud-panel/40 p-2"
      data-testid={testid ?? `column-${status}`}
      data-status={status}
    >
      <div className="mb-2 flex items-center justify-between">
        <span
          className={`rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${HUD_BADGE_CLASS[color]}`}
        >
          {STATUS_LABEL[status]}
        </span>
        <span className="text-[10px] tabular-nums text-hud-muted">{tasks.length}</span>
      </div>
      <div className="space-y-2">
        {tasks.length === 0 ? (
          <p className="px-1 py-2 text-[11px] text-hud-muted">—</p>
        ) : (
          tasks.map((task) => (
            <TaskCard key={task.id} task={task} busy={busy} onTransition={onTransition} />
          ))
        )}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  busy,
  onTransition,
}: {
  task: Task;
  busy: string | null;
  onTransition: (taskId: string, action: TaskAction) => void;
}): JSX.Element {
  const [open, setOpen] = useState(false);
  const color = taskStatusColor(task.status);
  const actions = actionsFor(task.status);
  const hasDetails = task.report !== "" || task.diff !== "";

  return (
    <article
      className="rounded-md border border-hud-border bg-hud-bg/60 p-2"
      data-testid="task-card"
      data-status={task.status}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-xs font-medium text-hud-text">{task.title}</h3>
        <span
          className={`shrink-0 rounded border px-1 py-0.5 text-[9px] uppercase tracking-wide ${HUD_BADGE_CLASS[color]}`}
          data-testid="task-status"
        >
          {STATUS_LABEL[task.status]}
        </span>
      </div>

      {task.acceptance_criteria.length > 0 && (
        <ul className="mt-1.5 space-y-0.5" data-testid="task-criteria">
          {task.acceptance_criteria.map((c, i) => (
            <li key={i} className="flex gap-1 text-[11px] text-hud-muted">
              <span className="text-hud-cyan/70">·</span>
              <span>{c}</span>
            </li>
          ))}
        </ul>
      )}

      {task.blocker && (
        <p className="mt-1.5 text-[11px] text-hud-red" data-testid="task-blocker">
          {task.blocker}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {actions.map((action) => {
          const c = ACTION_COLOR[action];
          const key = `task-${task.id}-${action}`;
          return (
            <button
              key={action}
              type="button"
              onClick={() => onTransition(task.id, action)}
              disabled={busy !== null}
              className={`rounded border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide transition disabled:opacity-50 ${HUD_BADGE_CLASS[c]} hover:brightness-125`}
              data-testid={`task-action-${action}`}
            >
              {busy === key ? "…" : ACTION_LABEL[action]}
            </button>
          );
        })}
        {hasDetails && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="ml-auto rounded border border-hud-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-hud-muted transition hover:text-hud-text"
            data-testid="task-toggle"
            aria-expanded={open}
          >
            {open ? "Réduire" : "Détails"}
          </button>
        )}
      </div>

      {open && hasDetails && (
        <div className="mt-2 space-y-2" data-testid="task-details">
          {task.report && (
            <div>
              <div className="hud-label mb-1">Report</div>
              <pre className="overflow-x-auto rounded bg-hud-bg p-2 text-[10px] text-hud-text">
                {task.report}
              </pre>
            </div>
          )}
          {task.diff && (
            <div>
              <div className="hud-label mb-1">Diff</div>
              <pre className="overflow-x-auto rounded bg-hud-bg p-2 text-[10px] text-hud-green">
                {task.diff}
              </pre>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

const NR_STATUS_CLASS: Record<string, string> = {
  done: "text-hud-green",
  finished: "text-hud-green",
  blocked: "text-hud-amber",
  failed: "text-hud-red",
};

function NightReportBlock({ report }: { report: NightReport | null }): JSX.Element {
  if (!report) {
    return (
      <section
        className="rounded-lg border border-hud-border bg-hud-panel/40 p-3 text-center text-xs text-hud-muted"
        data-testid="night-empty"
      >
        Pas encore de rapport de nuit
      </section>
    );
  }

  return (
    <section
      className="rounded-lg border border-hud-border bg-hud-panel/40 p-3"
      data-testid="mission-night"
    >
      <div className="mb-2 flex items-center gap-3">
        <h3 className="hud-label">Night Report</h3>
        {report.date && (
          <span className="text-[10px] tabular-nums text-hud-muted">{report.date}</span>
        )}
        {report.dry_run && (
          <span
            className={`rounded border px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide ${HUD_BADGE_CLASS.amber}`}
            data-testid="night-dryrun"
          >
            Dry-run
          </span>
        )}
      </div>

      <div className="mb-2 grid grid-cols-4 gap-2 text-xs">
        <Stat label="Faites" value={report.done} cls="text-hud-green" testid="night-done" />
        <Stat label="Bloquées" value={report.blocked} cls="text-hud-amber" testid="night-blocked" />
        <Stat label="Échecs" value={report.failed} cls="text-hud-red" testid="night-failed" />
        <Stat label="Coût $" value={report.cost_usd} cls="text-hud-cyan" testid="night-cost" />
      </div>

      {report.tasks.length > 0 && (
        <ul className="space-y-1" data-testid="night-tasks">
          {report.tasks.map((t, i) => (
            <li key={i} className="flex items-baseline gap-2 text-xs" data-testid="night-task">
              <span className={`shrink-0 uppercase ${NR_STATUS_CLASS[t.status] ?? "text-hud-muted"}`}>
                {t.status}
              </span>
              <span className="text-hud-text">{t.title}</span>
              {t.branch && <span className="text-hud-muted">({t.branch})</span>}
              {t.note && <span className="truncate text-hud-muted"> — {t.note}</span>}
            </li>
          ))}
        </ul>
      )}

      {report.blockers.length > 0 && (
        <div className="mt-2" data-testid="night-blockers">
          <h4 className="hud-label mb-1">Blockers</h4>
          <ul className="space-y-0.5">
            {report.blockers.map((b, i) => (
              <li key={i} className="text-xs text-hud-red">
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  cls,
  testid,
}: {
  label: string;
  value: number;
  cls: string;
  testid: string;
}): JSX.Element {
  return (
    <div className="flex flex-col" data-testid={testid}>
      <span className={`text-lg font-semibold tabular-nums ${cls}`}>{value}</span>
      <span className="hud-label mt-0.5">{label}</span>
    </div>
  );
}
