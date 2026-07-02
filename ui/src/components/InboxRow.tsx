import { HUD_BADGE_CLASS } from "../lib/theme";
import { categoryColor, type InboxItem } from "../lib/inbox";

interface Props {
  item: InboxItem;
}

/** Une ligne de la boîte de réception : badge catégorie, priorité, expéditeur, sujet, résumé. */
export default function InboxRow({ item }: Props): JSX.Element {
  const color = categoryColor(item.category);

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
      </div>
      <div className="truncate font-medium text-hud-text" title={item.subject}>
        {item.subject}
      </div>
      {item.summary && (
        <div className="truncate text-hud-muted" title={item.summary}>
          {item.summary}
        </div>
      )}
    </li>
  );
}
