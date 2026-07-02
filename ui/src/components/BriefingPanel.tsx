import { useState } from "react";
import { motion } from "framer-motion";
import { runAgent } from "../lib/api";
import { selectBriefing, type NightReport } from "../lib/briefing";
import type { SeqEvent } from "../lib/types";

interface Props {
  events: SeqEvent[];
}

/** Briefing du jour : texte de synthèse + sections dérivées du dernier `briefing.ready`. */
export default function BriefingPanel({ events }: Props): JSX.Element {
  const briefing = selectBriefing(events);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function trigger(action: string, fn: () => Promise<unknown>): Promise<void> {
    setBusy(action);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action échouée");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      className="hud-panel flex min-h-0 flex-col"
      aria-label="Briefing"
      data-testid="briefing-panel"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-hud-border px-3 py-2">
        <h2 className="hud-label">Briefing du jour</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => trigger("briefing", () => runAgent("ORACLE"))}
            disabled={busy !== null}
            className="rounded border border-hud-cyan/40 bg-hud-cyan/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-cyan transition hover:bg-hud-cyan/20 disabled:opacity-50"
            data-testid="briefing-generate"
          >
            {busy === "briefing" ? "Génération…" : "Générer le briefing"}
          </button>
          <button
            type="button"
            onClick={() => trigger("wake", () => runAgent("ATLAS", "deep-work"))}
            disabled={busy !== null}
            className="rounded border border-hud-amber/40 bg-hud-amber/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-hud-amber transition hover:bg-hud-amber/20 disabled:opacity-50"
            data-testid="briefing-wake"
          >
            {busy === "wake" ? "Réveil…" : "Lancer le réveil"}
          </button>
        </div>
      </header>

      {error && (
        <div className="border-b border-hud-red/30 px-3 py-1.5 text-[11px] text-hud-red" role="alert">
          {error}
        </div>
      )}

      {!briefing ? (
        <div
          className="flex flex-1 items-center justify-center p-6 text-center text-xs text-hud-muted"
          data-testid="briefing-empty"
        >
          Pas encore de briefing
        </div>
      ) : (
        <motion.div
          className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          {briefing.text && (
            <p className="text-sm leading-relaxed text-hud-text" data-testid="briefing-text">
              {briefing.text}
            </p>
          )}

          {briefing.sections.mails_urgents && briefing.sections.mails_urgents.length > 0 && (
            <Section title="Mails urgents" testid="briefing-section-mails">
              <ul className="space-y-1">
                {briefing.sections.mails_urgents.map((m, i) => (
                  <li key={i} className="text-xs text-hud-text">
                    <span className="text-hud-cyan/80">{m.sender}</span>
                    {m.subject && <span className="text-hud-muted"> · {m.subject}</span>}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {briefing.sections.calendrier && briefing.sections.calendrier.length > 0 && (
            <Section title="Calendrier" testid="briefing-section-calendrier">
              <ul className="space-y-1">
                {briefing.sections.calendrier.map((c, i) => (
                  <li key={i} className="text-xs text-hud-text">
                    <span className="tabular-nums text-hud-amber">{c.time}</span>
                    {c.title && <span className="text-hud-text"> — {c.title}</span>}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {briefing.sections.night_report && (
            <NightReportBlock report={briefing.sections.night_report} />
          )}

          {briefing.sections.meteo && (
            <Section title="Météo" testid="briefing-section-meteo">
              <p className="text-xs text-hud-text">{briefing.sections.meteo}</p>
            </Section>
          )}
        </motion.div>
      )}
    </section>
  );
}

function Section({
  title,
  testid,
  children,
}: {
  title: string;
  testid: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <section data-testid={testid}>
      <h3 className="hud-label mb-1.5">{title}</h3>
      {children}
    </section>
  );
}

const STATUS_CLASS: Record<string, string> = {
  done: "text-hud-green",
  finished: "text-hud-green",
  blocked: "text-hud-amber",
  failed: "text-hud-red",
};

function NightReportBlock({ report }: { report: NightReport }): JSX.Element {
  return (
    <section data-testid="briefing-section-night">
      <div className="mb-2 flex items-center gap-3">
        <h3 className="hud-label">Night Report</h3>
        {report.date && <span className="text-[10px] tabular-nums text-hud-muted">{report.date}</span>}
      </div>

      <div className="mb-2 grid grid-cols-4 gap-2 text-xs">
        <Stat label="Faites" value={report.done} cls="text-hud-green" testid="night-done" />
        <Stat label="Bloquées" value={report.blocked} cls="text-hud-amber" testid="night-blocked" />
        <Stat label="Échecs" value={report.failed} cls="text-hud-red" testid="night-failed" />
        <Stat
          label="Coût $"
          value={report.cost_usd}
          cls="text-hud-cyan"
          testid="night-cost"
        />
      </div>

      {report.tasks.length > 0 && (
        <ul className="space-y-1" data-testid="night-tasks">
          {report.tasks.map((t, i) => (
            <li key={i} className="flex items-baseline gap-2 text-xs" data-testid="night-task">
              <span className={`shrink-0 uppercase ${STATUS_CLASS[t.status] ?? "text-hud-muted"}`}>
                {t.status}
              </span>
              <span className="text-hud-text">{t.title}</span>
              {t.branch && <span className="text-hud-muted">({t.branch})</span>}
              {t.note && <span className="truncate text-hud-muted"> — {t.note}</span>}
            </li>
          ))}
        </ul>
      )}

      {report.blockers.length > 0 && (
        <div className="mt-2" data-testid="night-blockers">
          <h4 className="hud-label mb-1">Blockers</h4>
          <ul className="space-y-0.5">
            {report.blockers.map((b, i) => (
              <li key={i} className="text-xs text-hud-red">
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  cls,
  testid,
}: {
  label: string;
  value: number;
  cls: string;
  testid: string;
}): JSX.Element {
  return (
    <div className="flex flex-col" data-testid={testid}>
      <span className={`text-lg font-semibold tabular-nums ${cls}`}>{value}</span>
      <span className="hud-label mt-0.5">{label}</span>
    </div>
  );
}
