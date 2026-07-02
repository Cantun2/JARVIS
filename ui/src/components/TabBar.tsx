export type TabId = "dashboard" | "inbox" | "briefing";

interface Props {
  active: TabId;
  onChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "inbox", label: "Inbox" },
  { id: "briefing", label: "Briefing" },
];

/** Barre d'onglets HUD : accent cyan sur l'onglet actif. */
export default function TabBar({ active, onChange }: Props): JSX.Element {
  return (
    <nav className="flex items-center gap-1" role="tablist" aria-label="Navigation" data-testid="tab-bar">
      {TABS.map((tab) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.id)}
            data-testid={`tab-${tab.id}`}
            className={`hud-label rounded-md border px-3 py-1.5 transition ${
              selected
                ? "border-hud-cyan/50 bg-hud-cyan/10 text-hud-cyan"
                : "border-transparent text-hud-muted hover:text-hud-text"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
