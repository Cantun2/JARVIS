import { useState } from "react";
import { HUD_BADGE_CLASS } from "../lib/theme";
import { categoryColor, type InboxItem } from "../lib/inbox";

interface Props {
  item: InboxItem;
  onReclassify?: (id: string, category: string) => void | Promise<void>;
}

const CATEGORIES = ["urgent", "action", "info", "newsletter", "spam"] as const;

/** Une ligne de la boîte : badge catégorie, priorité, expéditeur, sujet, résumé,
 *  + (Phase 4) brouillon dépliable et correction de classement en un clic. */
export default function InboxRow({ item, onReclassify }: Props): JSX.Element {
  const color = categoryColor(item.category);
  const [showDraft, setShowDraft] = useState(false);

  return (
    <li
      className="flex flex-col gap-1 px-3 py-2.5 text-xs hover:bg-white/[0.02]"
      data-testid="inbox-row"
      data-category={item.category}
      data-color={color}
    >
      <div className="flex items-center gap-2">
        <span
          className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${HUD_BADGE_CLASS[color]}`}
          data-testid="inbox-category"
        >
          {item.category || "—"}
        </span>
        <span
          className="shrink-0 tabular-nums text-hud-muted"
          title="Priorité"
          data-testid="inbox-priority"
        >
          P{item.priority}
        </span>
        <span className="truncate text-hud-cyan/80" title={item.sender}>
          {item.sender}
        </span>
        {item.corrected && (
          <span
            className="shrink-0 rounded border border-hud-green/40 px-1 text-[10px] text-hud-green"
            data-testid="inbox-corrected"
            title="Classement corrigé — règle apprise"
          >
            corrigé
          </span>
        )}
      </div>
      <div className="truncate font-medium text-hud-text" title={item.subject}>
        {item.subject}
      </div>
      {item.summary && (
        <div className="truncate text-hud-muted" title={item.summary}>
          {item.summary}
        </div>
      )}

      <div className="mt-1 flex flex-wrap items-center gap-2">
        {onReclassify && (
          <label className="flex items-center gap-1 text-[10px] text-hud-muted">
            Classer
            <select
              value={item.category}
              onChange={(e) => void onReclassify(item.id, e.target.value)}
              className="rounded border border-hud-border bg-transparent px-1 py-0.5 text-[10px] text-hud-text focus:border-hud-cyan/50 focus:outline-none"
              data-testid="inbox-reclassify"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c} className="bg-hud-bg">
                  {c}
                </option>
              ))}
            </select>
          </label>
        )}
        {item.draft && (
          <button
            type="button"
            onClick={() => setShowDraft((v) => !v)}
            className="rounded border border-hud-amber/40 bg-hud-amber/10 px-1.5 py-0.5 text-[10px] font-medium text-hud-amber transition hover:bg-hud-amber/20"
            data-testid="inbox-draft-toggle"
          >
            {showDraft ? "Masquer le brouillon" : "✎ Brouillon"}
          </button>
        )}
      </div>

      {item.draft && showDraft && (
        <pre
          className="mt-1 whitespace-pre-wrap rounded border border-hud-border bg-black/30 p-2 text-[11px] text-hud-text"
          data-testid="inbox-draft"
        >
          {item.draft}
        </pre>
      )}
    </li>
  );
}
