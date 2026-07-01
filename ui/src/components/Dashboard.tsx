import { motion } from "framer-motion";
import AgentStatusArc from "./AgentStatusArc";
import Clock from "./Clock";
import ConnectionBadge from "./ConnectionBadge";
import EventFeed from "./EventFeed";
import type { Agent, Health, SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
  agents: Agent[];
  health: Health | null;
  connected: boolean;
}

/** Layout HUD principal : en-tête (horloge + lien), arc d'agents, flux live. */
export default function Dashboard({ events, agents, health, connected }: Props): JSX.Element {
  return (
    <div className="flex h-full flex-col gap-4 p-4 md:p-6">
      {/* En-tête */}
      <motion.header
        className="hud-panel flex items-center justify-between gap-4 px-4 py-3 md:px-6"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className="flex items-center gap-4">
          <div>
            <div className="text-sm font-bold tracking-[0.3em] text-hud-cyan">JARVIS</div>
            <div className="hud-label">Mission Control</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Clock />
          <ConnectionBadge connected={connected} health={health} />
        </div>
      </motion.header>

      {/* Corps : arc d'agents + flux */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex min-h-0 flex-col gap-4 lg:col-span-1">
          <AgentStatusArc agents={agents} events={events} />
          <SummaryPanel agents={agents} events={events} health={health} />
        </div>
        <div className="flex min-h-0 lg:col-span-2">
          <div className="flex min-h-0 w-full flex-col">
            <EventFeed events={events} />
          </div>
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
