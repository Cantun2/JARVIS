import { useEffect, useState } from "react";

/** Horloge + date, typo mono. Se met à jour chaque seconde. */
export default function Clock(): JSX.Element {
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const time = now.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const date = now.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex flex-col" aria-label="Horloge">
      <div
        className="text-3xl font-semibold tabular-nums tracking-wider text-hud-cyan"
        data-testid="clock-time"
      >
        {time}
      </div>
      <div className="mt-1 text-xs capitalize text-hud-muted" data-testid="clock-date">
        {date}
      </div>
    </div>
  );
}
