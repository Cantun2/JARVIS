// Sélecteur pur : dérive le dernier briefing du flux d'événements.
// Payload EXACT de `briefing.ready` (tous les champs de `sections` optionnels) :
//   {
//     text: string,
//     sections: {
//       mails_urgents?: { sender, subject }[],
//       calendrier?: { time, title }[],
//       night_report?: {
//         date, done, blocked, failed, cost_usd,
//         tasks: { title, status, branch?, note? }[],
//         blockers: string[],
//       },
//       meteo?: string,
//     },
//   }
import type { SeqEvent } from "./types";

export interface UrgentMail {
  sender: string;
  subject: string;
}

export interface CalendarEntry {
  time: string;
  title: string;
}

export interface NightTask {
  title: string;
  status: string;
  branch?: string;
  note?: string;
}

export interface NightReport {
  date: string;
  done: number;
  blocked: number;
  failed: number;
  cost_usd: number;
  tasks: NightTask[];
  blockers: string[];
}

export interface BriefingSections {
  mails_urgents?: UrgentMail[];
  calendrier?: CalendarEntry[];
  night_report?: NightReport;
  meteo?: string;
}

export interface Briefing {
  text: string;
  sections: BriefingSections;
}

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}

function str(r: Record<string, unknown>, key: string): string {
  const v = r[key];
  return typeof v === "string" ? v : "";
}

function num(r: Record<string, unknown>, key: string): number {
  const v = r[key];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

function strArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function parseUrgentMails(v: unknown): UrgentMail[] | undefined {
  if (!Array.isArray(v)) return undefined;
  return v.map((raw) => {
    const r = asRecord(raw);
    return { sender: str(r, "sender"), subject: str(r, "subject") };
  });
}

function parseCalendar(v: unknown): CalendarEntry[] | undefined {
  if (!Array.isArray(v)) return undefined;
  return v.map((raw) => {
    const r = asRecord(raw);
    return { time: str(r, "time"), title: str(r, "title") };
  });
}

function parseNightReport(v: unknown): NightReport | undefined {
  if (!v || typeof v !== "object" || Array.isArray(v)) return undefined;
  const r = asRecord(v);
  const tasks: NightTask[] = Array.isArray(r.tasks)
    ? r.tasks.map((raw) => {
        const t = asRecord(raw);
        const task: NightTask = { title: str(t, "title"), status: str(t, "status") };
        if (typeof t.branch === "string") task.branch = t.branch;
        if (typeof t.note === "string") task.note = t.note;
        return task;
      })
    : [];
  return {
    date: str(r, "date"),
    done: num(r, "done"),
    blocked: num(r, "blocked"),
    failed: num(r, "failed"),
    cost_usd: num(r, "cost_usd"),
    tasks,
    blockers: strArray(r.blockers),
  };
}

/**
 * Retourne le dernier briefing (plus grand `seq` parmi les `briefing.ready`),
 * ou null si aucun. Accès défensif : toutes les sections sont optionnelles.
 * Fonction pure.
 */
export function selectBriefing(events: SeqEvent[]): Briefing | null {
  let latest: SeqEvent | null = null;
  for (const ev of events) {
    if (ev.type !== "briefing.ready") continue;
    if (!latest || ev.seq > latest.seq) latest = ev;
  }
  if (!latest) return null;

  const sectionsRaw = asRecord(latest.payload.sections);
  const sections: BriefingSections = {};
  const urgents = parseUrgentMails(sectionsRaw.mails_urgents);
  if (urgents) sections.mails_urgents = urgents;
  const calendrier = parseCalendar(sectionsRaw.calendrier);
  if (calendrier) sections.calendrier = calendrier;
  const nightReport = parseNightReport(sectionsRaw.night_report);
  if (nightReport) sections.night_report = nightReport;
  if (typeof sectionsRaw.meteo === "string") sections.meteo = sectionsRaw.meteo;

  return { text: str(latest.payload, "text"), sections };
}
