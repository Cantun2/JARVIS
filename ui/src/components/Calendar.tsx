import { monthMatrix, todayYmd, toYmd } from "../lib/date";

interface Props {
  year: number;
  /** Mois 1-12. */
  month: number;
  /** Jour sélectionné (YYYY-MM-DD). */
  selected: string;
  /** Dates portant une pastille (YYYY-MM-DD). */
  marked: Set<string>;
  onSelectDay: (ymd: string) => void;
  onPrevMonth?: () => void;
  onNextMonth?: () => void;
}

const WEEKDAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const MONTHS = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

/**
 * Grille mensuelle HUD : navigation mois précédent/suivant, en-têtes des jours
 * (lundi→dimanche), un bouton par jour (sélection, pastille, hors-mois estompé,
 * anneau sur aujourd'hui).
 */
export default function Calendar({
  year,
  month,
  selected,
  marked,
  onSelectDay,
  onPrevMonth,
  onNextMonth,
}: Props): JSX.Element {
  const weeks = monthMatrix(year, month);
  const today = todayYmd();
  const title = `${MONTHS[month - 1] ?? ""} ${year}`;

  return (
    <div className="hud-panel p-3" data-testid="calendar" aria-label="Calendrier">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          className="rounded border border-hud-border px-2 py-0.5 text-xs text-hud-muted transition hover:text-hud-cyan"
          data-testid="calendar-prev"
          aria-label="Mois précédent"
        >
          ‹
        </button>
        <span className="hud-label" data-testid="calendar-title">
          {title}
        </span>
        <button
          type="button"
          onClick={onNextMonth}
          className="rounded border border-hud-border px-2 py-0.5 text-xs text-hud-muted transition hover:text-hud-cyan"
          data-testid="calendar-next"
          aria-label="Mois suivant"
        >
          ›
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="hud-label pb-1 text-center">
            {wd}
          </div>
        ))}

        {weeks.map((week) =>
          week.map((day) => {
            const ymd = toYmd(day);
            const inMonth = day.getMonth() === month - 1;
            const isSelected = ymd === selected;
            const isToday = ymd === today;
            const isMarked = marked.has(ymd);
            return (
              <button
                key={ymd}
                type="button"
                onClick={() => onSelectDay(ymd)}
                data-testid="calendar-day"
                data-ymd={ymd}
                data-selected={isSelected}
                data-in-month={inMonth}
                data-today={isToday}
                data-marked={isMarked}
                className={`relative flex h-9 flex-col items-center justify-center rounded text-xs tabular-nums transition ${
                  isSelected
                    ? "bg-hud-cyan/20 text-hud-cyan"
                    : inMonth
                      ? "text-hud-text hover:bg-hud-border/50"
                      : "text-hud-muted/40 hover:bg-hud-border/30"
                } ${isToday ? "ring-1 ring-hud-cyan/60" : ""}`}
                aria-pressed={isSelected}
              >
                <span>{day.getDate()}</span>
                {isMarked && (
                  <span
                    className="absolute bottom-1 h-1 w-1 rounded-full bg-hud-amber"
                    data-testid="calendar-dot"
                    aria-hidden="true"
                  />
                )}
              </button>
            );
          }),
        )}
      </div>
    </div>
  );
}
