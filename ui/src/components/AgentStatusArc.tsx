import { useState } from "react";
import { motion } from "framer-motion";
import { HUD_FILL_CLASS, agentColor, overlayAgentStatus } from "../lib/theme";
import type { Agent, SeqEvent } from "../lib/types";

interface Props {
  agents: Agent[];
  /** Événements récents ; les agent.* mettent à jour le statut affiché. */
  events?: SeqEvent[];
  /** Clic sur un agent conversationnel : ouvrir le chat avec lui. */
  onOpenChat?: ((agent: string) => void) | undefined;
  /** Clic sur un agent de tâche : le lancer (peut être async). */
  onRunAgent?: ((name: string) => void | Promise<void>) | undefined;
}

/** Pastilles disposées en arc, une par agent, colorées par statut et cliquables. */
export default function AgentStatusArc({
  agents,
  events = [],
  onOpenChat,
  onRunAgent,
}: Props): JSX.Element {
  const resolved = overlayAgentStatus(agents, events);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  async function activate(agent: Agent): Promise<void> {
    if (agent.conversational) {
      onOpenChat?.(agent.name);
      return;
    }
    if (!onRunAgent) return;
    setBusy((b) => ({ ...b, [agent.name]: true }));
    setError(null);
    try {
      await onRunAgent(agent.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Échec de ${agent.name}`);
    } finally {
      setBusy((b) => ({ ...b, [agent.name]: false }));
    }
  }

  return (
    <section className="hud-panel px-4 py-3" aria-label="Statut des agents">
      <header className="mb-3 flex items-center justify-between">
        <h2 className="hud-label">Flotte d'agents</h2>
        <span className="text-[10px] tabular-nums text-hud-muted">{resolved.length}</span>
      </header>

      {error && (
        <div className="mb-2 text-[11px] text-hud-red" role="alert">
          {error}
        </div>
      )}

      {resolved.length === 0 ? (
        <div className="py-4 text-center text-xs text-hud-muted">Aucun agent</div>
      ) : (
        <ul
          className="flex flex-wrap items-end justify-center gap-x-5 gap-y-4"
          data-testid="agent-arc"
        >
          {resolved.map((agent, i) => {
            const color = agentColor(agent.status, agent.enabled);
            const running = busy[agent.name] === true;
            const pulsing = agent.status === "started" || running;
            // Léger décalage vertical pour évoquer un arc.
            const lift = arcLift(i, resolved.length);
            return (
              <li
                key={agent.name}
                className="flex w-16 flex-col items-center"
                style={{ transform: `translateY(${lift}px)` }}
              >
                <button
                  type="button"
                  disabled={!agent.enabled || running}
                  onClick={() => void activate(agent)}
                  data-testid="agent-dot"
                  data-agent={agent.name}
                  data-status={agent.status}
                  data-enabled={agent.enabled ? "true" : "false"}
                  data-color={color}
                  data-conversational={agent.conversational ? "true" : "false"}
                  title={`${agent.name} — ${agent.enabled ? agent.status : "désactivé"}`}
                  aria-label={`${agent.name} (${agent.enabled ? agent.status : "désactivé"})`}
                  className="flex w-full flex-col items-center gap-1.5 rounded-md py-1 transition enabled:hover:bg-white/[0.03] disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-1 focus-visible:ring-hud-cyan/50"
                >
                  <motion.span
                    className={`h-3 w-3 rounded-full ${HUD_FILL_CLASS[color]} ${
                      pulsing ? "animate-pulse-glow" : ""
                    }`}
                    initial={{ scale: 0.6, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.25, delay: i * 0.03 }}
                    aria-hidden
                  />
                  <span className="max-w-full truncate text-[10px] uppercase tracking-wide text-hud-muted">
                    {agent.name}
                  </span>
                </button>
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
