import { AnimatePresence, motion } from "framer-motion";
import EventRow from "./EventRow";
import type { SeqEvent } from "../lib/types";

/** Limite d'affichage du flux (le plus récent en haut). */
export const FEED_LIMIT = 200;

interface Props {
  events: SeqEvent[];
}

/** Flux live des événements, le plus récent en haut, plafonné à FEED_LIMIT. */
export default function EventFeed({ events }: Props): JSX.Element {
  const shown = events.slice(0, FEED_LIMIT);

  return (
    <section className="hud-panel flex min-h-0 flex-col" aria-label="Flux d'événements">
      <header className="flex items-center justify-between border-b border-hud-border px-3 py-2">
        <h2 className="hud-label">Flux d'événements</h2>
        <span className="text-[10px] tabular-nums text-hud-muted" data-testid="feed-count">
          {shown.length}
        </span>
      </header>

      {shown.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6 text-xs text-hud-muted">
          En attente d'événements…
        </div>
      ) : (
        <ul
          className="min-h-0 flex-1 divide-y divide-hud-border/60 overflow-y-auto"
          data-testid="event-feed"
        >
          <AnimatePresence initial={false}>
            {shown.map((ev) => (
              <motion.div
                key={ev.seq}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
              >
                <EventRow event={ev} />
              </motion.div>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
