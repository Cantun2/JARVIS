// Client REST typé du backend jarvis-suit.
//
// En dev, on tape des chemins relatifs (`/api/...`) : le proxy Vite les renvoie
// vers VITE_API_BASE. En build/prod (ou hors proxy), on préfixe par API_BASE.
import type {
  Agent,
  EventsResponse,
  Health,
  RunAgentResponse,
} from "./types";

/**
 * Base API. Vide par défaut => chemins relatifs (proxifiés par Vite en dev,
 * servis par le même origin en prod). Surchargée par VITE_API_BASE si fournie.
 */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Base WebSocket dérivée : http(s) -> ws(s). Vide => same-origin. */
export function wsBase(base: string = API_BASE): string {
  if (base) {
    return base.replace(/^http/, "ws");
  }
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}`;
  }
  return "";
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    headers: { Accept: "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** GET /api/health */
export function getHealth(): Promise<Health> {
  return getJson<Health>("/api/health");
}

/** GET /api/agents */
export function getAgents(): Promise<Agent[]> {
  return getJson<Agent[]>("/api/agents");
}

/** GET /api/events?since=&limit= */
export function getEvents(since = 0, limit = 200): Promise<EventsResponse> {
  const qs = new URLSearchParams({ since: String(since), limit: String(limit) });
  return getJson<EventsResponse>(`/api/events?${qs.toString()}`);
}

/** POST /api/agents/{name}/run */
export function runAgent(
  name: string,
  profile?: string,
): Promise<RunAgentResponse> {
  const body = profile === undefined ? {} : { profile };
  return getJson<RunAgentResponse>(`/api/agents/${encodeURIComponent(name)}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}
