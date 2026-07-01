import type { Health } from "../lib/types";

interface Props {
  connected: boolean;
  health: Health | null;
}

/** Pastille d'état du lien WebSocket + méta backend (mode / version). */
export default function ConnectionBadge({ connected, health }: Props): JSX.Element {
  const dotClass = connected ? "bg-hud-green" : "bg-hud-red";
  const label = connected ? "EN LIGNE" : "HORS LIGNE";

  return (
    <div
      className="hud-panel flex items-center gap-3 px-3 py-2"
      role="status"
      aria-live="polite"
      data-connected={connected ? "true" : "false"}
    >
      <span className="relative flex h-2.5 w-2.5">
        {connected && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full bg-hud-green opacity-60"
            aria-hidden
          />
        )}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${dotClass}`} aria-hidden />
      </span>
      <div className="leading-tight">
        <div className="text-xs font-semibold tracking-wide text-hud-text">{label}</div>
        {health && (
          <div className="hud-label" data-testid="health-meta">
            {health.mode} · v{health.version} · {health.inference_backend}
          </div>
        )}
      </div>
    </div>
  );
}
