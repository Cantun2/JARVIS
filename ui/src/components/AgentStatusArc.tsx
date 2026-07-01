import { motion } from "framer-motion";
import { HUD_FILL_CLASS, agentColor, overlayAgentStatus } from "../lib/theme";
import type { Agent, SeqEvent } from "../lib/types";

interface Props {
  agents: Agent[];
  /** Événements récents ; les agent.* mettent à jour le statut affiché. */
  events?: SeqEvent[];
}

/** Pastilles disposées en arc, une par agent, colorées par statut. */
export default function AgentStatusArc({ agents, events = [] }: Props): JSX.Element {
  const resolved = overlayAgentStatus(agents, events);

  return (
    <section className="hud-panel px-4 py-3" aria-label="Statut des agents">
      <header className="mb-3 flex items-center justify-between">
        <h2 className="hud-label">Flotte d'agents</h2>
        <span className="text-[10px] tabular-nums text-hud-muted">{resolved.length}</span>
      </header>

      {resolved.length === 0 ? (
        <div className="py-4 text-center text-xs text-hud-muted">Aucun agent</div>
      ) : (
        <ul
          className="flex flex-wrap items-end justify-center gap-x-5 gap-y-4"
          data-testid="agent-arc"
        >
          {resolved.map((agent, i) => {
            const color = agentColor(agent.status, agent.enabled);
            // Léger décalage vertical pour évoquer un arc.
            const lift = arcLift(i, resolved.length);
            return (
              <li
                key={agent.name}
                className="flex w-16 flex-col items-center gap-1.5"
                data-testid="agent-dot"
                data-agent={agent.name}
                data-status={agent.status}
                data-enabled={agent.enabled ? "true" : "false"}
                data-color={color}
                title={`${agent.name} — ${agent.enabled ? agent.status : "désactivé"}`}
                style={{ transform: `translateY(${lift}px)` }}
              >
                <motion.span
                  className={`h-3 w-3 rounded-full ${HUD_FILL_CLASS[color]} ${
                    agent.status === "started" ? "animate-pulse-glow" : ""
                  }`}
                  initial={{ scale: 0.6, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.25, delay: i * 0.03 }}
                  aria-hidden
                />
                <span className="max-w-full truncate text-[10px] uppercase tracking-wide text-hud-muted">
                  {agent.name}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** Décalage vertical en pixels pour l'effet d'arc (concave vers le haut). */
function arcLift(index: number, total: number): number {
  if (total <= 1) return 0;
  const t = index / (total - 1); // 0..1
  const centered = (t - 0.5) * 2; // -1..1
  return -Math.round((1 - centered * centered) * 10); // 0 aux bords, -10 au centre
}
