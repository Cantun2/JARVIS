import AgentStatusArc from "./AgentStatusArc";
import EventFeed from "./EventFeed";
import type { Agent, Health, SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
  agents: Agent[];
  health: Health | null;
  /** Ouvrir le chat avec un agent conversationnel (clic sur l'arc). */
  onOpenChat?: ((agent: string) => void) | undefined;
  /** Lancer un agent de tâche (clic sur l'arc). */
  onRunAgent?: ((name: string) => void | Promise<void>) | undefined;
}

/** Layout HUD principal : arc d'agents + flux live (en-tête géré par App). */
export default function Dashboard({
  events,
  agents,
  health,
  onOpenChat,
  onRunAgent,
}: Props): JSX.Element {
  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="flex min-h-0 flex-col gap-4 lg:col-span-1">
        <AgentStatusArc
          agents={agents}
          events={events}
          onOpenChat={onOpenChat}
          onRunAgent={onRunAgent}
        />
        <SummaryPanel agents={agents} events={events} health={health} />
      </div>
      <div className="flex min-h-0 lg:col-span-2">
        <div className="flex min-h-0 w-full flex-col">
          <EventFeed events={events} />
        </div>
      </div>
    </div>
  );
}

/** Petit panneau de métriques dérivées (agents actifs, dernier événement). */
function SummaryPanel({
  agents,
  events,
  health,
}: {
  agents: Agent[];
  events: SeqEvent[];
  health: Health | null;
}): JSX.Element {
  const enabled = agents.filter((a) => a.enabled).length;
  const running = agents.filter((a) => a.status === "started").length;
  const failed = agents.filter((a) => a.status === "failed").length;
  const last = events[0];

  return (
    <section className="hud-panel grid grid-cols-3 gap-3 p-4" aria-label="Résumé">
      <Metric label="Agents" value={`${enabled}/${agents.length}`} />
      <Metric label="Actifs" value={String(running)} accent="amber" />
      <Metric label="Échecs" value={String(failed)} accent={failed > 0 ? "red" : "green"} />
      <div className="col-span-3 border-t border-hud-border pt-3">
        <div className="hud-label">Dernier événement</div>
        <div className="mt-1 truncate text-xs text-hud-text">
          {last ? `${last.type} · ${last.source}` : "—"}
        </div>
      </div>
      {health && (
        <div className="col-span-3">
          <div className="hud-label">Desktop</div>
          <div className="mt-1 text-xs text-hud-text">
            {health.desktop_backend}
            {health.placement_available ? " · placement OK" : " · placement indispo"}
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
  accent = "cyan",
}: {
  label: string;
  value: string;
  accent?: "cyan" | "amber" | "red" | "green";
}): JSX.Element {
  const cls = {
    cyan: "text-hud-cyan",
    amber: "text-hud-amber",
    red: "text-hud-red",
    green: "text-hud-green",
  }[accent];
  return (
    <div className="flex flex-col">
      <span className={`text-xl font-semibold tabular-nums ${cls}`}>{value}</span>
      <span className="hud-label mt-0.5">{label}</span>
    </div>
  );
}
