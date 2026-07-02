import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import InboxRow from "./InboxRow";
import { runAgent } from "../lib/api";
import { HUD_BADGE_CLASS } from "../lib/theme";
import { categoryColor, selectInbox } from "../lib/inbox";
import type { SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
}

/** Ordre d'affichage des compteurs par catégorie. */
const CATEGORY_ORDER = ["urgent", "action", "info", "newsletter", "spam"] as const;

/** Boîte de réception : liste lecture seule des mails triés par HERMES. */
export default function InboxPanel({ events }: Props): JSX.Element {
  const items = selectInbox(events);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const counts = items.reduce<Record<string, number>>((acc, it) => {
    const key = it.category || "autre";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  async function refresh(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      await runAgent("HERMES");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec du tri");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      className="hud-panel flex min-h-0 flex-col"
      aria-label="Boîte de réception"
      data-testid="inbox-panel"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-hud-border px-3 py-2">
        <div className="flex items-center gap-3">
          <h2 className="hud-label">Boîte de réception</h2>
          <span
            className="text-[10px] tabular-nums text-hud-muted"
            data-testid="inbox-count"
          >
            {items.length}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            {CATEGORY_ORDER.filter((c) => counts[c]).map((c) => (
              <span
                key={c}
                className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${HUD_BADGE_CLASS[categoryColor(c)]}`}
                data-testid="inbox-cat-count"
                data-category={c}
              >
                {c} {counts[c]}
              </span>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="rounded border border-hud-cyan/40 bg-hud-cyan/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-cyan transition hover:bg-hud-cyan/20 disabled:opacity-50"
          data-testid="inbox-refresh"
        >
          {loading ? "Tri en cours…" : "Rafraîchir le tri"}
        </button>
      </header>

      {error && (
        <div className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red" role="alert">
          {error}
        </div>
      )}

      {items.length === 0 ? (
        <div
          className="flex flex-1 items-center justify-center p-6 text-center text-xs text-hud-muted"
          data-testid="inbox-empty"
        >
          Aucun mail trié — lance HERMES
        </div>
      ) : (
        <ul
          className="min-h-0 flex-1 divide-y divide-hud-border/60 overflow-y-auto"
          data-testid="inbox-list"
        >
          <AnimatePresence initial={false}>
            {items.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
              >
                <InboxRow item={item} />
              </motion.div>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
