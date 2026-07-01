import { HUD_BADGE_CLASS, eventColor, summarizePayload } from "../lib/theme";
import type { SeqEvent } from "../lib/types";

interface Props {
  event: SeqEvent;
}

/** Une ligne du flux : heure mono, badge type coloré, source, résumé payload. */
export default function EventRow({ event }: Props): JSX.Element {
  const color = eventColor(event.type);
  const time = formatTime(event.ts);
  const summary = summarizePayload(event.payload);

  return (
    <li
      className="flex items-start gap-3 px-3 py-2 text-xs hover:bg-white/[0.02]"
      data-testid="event-row"
      data-type={event.type}
      data-color={color}
    >
      <span className="shrink-0 tabular-nums text-hud-muted" title={event.ts}>
        {time}
      </span>
      <span
        className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium ${HUD_BADGE_CLASS[color]}`}
        data-testid="event-badge"
      >
        {event.type}
      </span>
      <span className="shrink-0 text-hud-cyan/80">{event.source}</span>
      {summary && (
        <span className="truncate text-hud-muted" title={summary}>
          {summary}
        </span>
      )}
    </li>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
