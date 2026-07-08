// Client REST typé du backend jarvis-suit.
//
// En dev, on tape des chemins relatifs (`/api/...`) : le proxy Vite les renvoie
// vers VITE_API_BASE. En build/prod (ou hors proxy), on préfixe par API_BASE.
import type {
  Agent,
  ChatHistory,
  ChatReply,
  Conversation,
  CreateProjectResponse,
  CreateTodo,
  Draft,
  EchoReply,
  EventsResponse,
  Health,
  InboxResponse,
  NightReport,
  Project,
  RunAgentResponse,
  Task,
  TaskAction,
  Todo,
  TodoStatus,
  UpdateTodo,
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

// --- Mission Control ---------------------------------------------------------

/** GET /api/projects */
export function getProjects(): Promise<Project[]> {
  return getJson<Project[]>("/api/projects");
}

/** POST /api/projects — génère un backlog pour un objectif. */
export function createProject(
  goal: string,
  name?: string,
): Promise<CreateProjectResponse> {
  const body = name === undefined ? { goal } : { goal, name };
  return getJson<CreateProjectResponse>("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

/** GET /api/projects/{id}/tasks */
export function getProjectTasks(projectId: string): Promise<Task[]> {
  return getJson<Task[]>(`/api/projects/${encodeURIComponent(projectId)}/tasks`);
}

/** POST /api/tasks/{id}/transition */
export function transitionTask(taskId: string, action: TaskAction): Promise<Task> {
  return getJson<Task>(`/api/tasks/${encodeURIComponent(taskId)}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ action }),
  });
}

/** POST /api/night/run — lance la nuit (dry-run côté backend). */
export function runNight(projectId: string): Promise<NightReport> {
  return getJson<NightReport>("/api/night/run", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
}

/** GET /api/night/report — dernier rapport de nuit ou null. */
export function getNightReport(): Promise<NightReport | null> {
  return getJson<NightReport | null>("/api/night/report");
}

// --- Phase 4 — Les sens (ECHO / Inbox v2) ------------------------------------

/** POST /api/echo/say — envoie une commande « parlée » à ECHO. */
export function sayToEcho(utterance: string): Promise<EchoReply> {
  return getJson<EchoReply>("/api/echo/say", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ utterance }),
  });
}

/** GET /api/inbox — boîte enrichie (brouillon + drapeau correction). */
export function getInbox(): Promise<InboxResponse> {
  return getJson<InboxResponse>("/api/inbox");
}

/** POST /api/inbox/{id}/reclassify — corrige la catégorie (devient une règle apprise). */
export async function reclassifyMail(id: string, category: string): Promise<void> {
  await getJson<Record<string, string>>(
    `/api/inbox/${encodeURIComponent(id)}/reclassify`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ category }),
    },
  );
}

/** GET /api/inbox/drafts — brouillons de réponse (jamais envoyés). */
export function getDrafts(): Promise<Draft[]> {
  return getJson<Draft[]>("/api/inbox/drafts");
}

// --- Chat multi-tours (agents conversationnels) ------------------------------

/** POST /api/chat — envoie un message à un agent conversationnel. */
export function postChat(
  agent: string,
  message: string,
  conversationId?: string,
  project?: string,
): Promise<ChatReply> {
  const body: Record<string, string> = { agent, message };
  if (conversationId !== undefined) body.conversation_id = conversationId;
  if (project !== undefined) body.project = project;
  return getJson<ChatReply>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

/** GET /api/chat/{conversation_id} — historique complet d'une conversation. */
export function getChatHistory(conversationId: string): Promise<ChatHistory> {
  return getJson<ChatHistory>(`/api/chat/${encodeURIComponent(conversationId)}`);
}

/** GET /api/conversations?agent=NAME — conversations (optionnellement filtrées par agent). */
export function getConversations(agent?: string): Promise<Conversation[]> {
  const qs = agent === undefined ? "" : `?${new URLSearchParams({ agent }).toString()}`;
  return getJson<Conversation[]>(`/api/conversations${qs}`);
}

// --- Agenda (CHRONOS : todos / rendez-vous / rappels) ------------------------

/** GET /api/todos?date=YYYY-MM-DD — éléments d'agenda d'un jour. */
export function getTodos(date: string): Promise<Todo[]> {
  const qs = new URLSearchParams({ date });
  return getJson<Todo[]>(`/api/todos?${qs.toString()}`);
}

/** GET /api/todos/month?year=YYYY&month=M — éléments d'agenda d'un mois. */
export function getTodosMonth(year: number, month: number): Promise<Todo[]> {
  const qs = new URLSearchParams({ year: String(year), month: String(month) });
  return getJson<Todo[]>(`/api/todos/month?${qs.toString()}`);
}

/** POST /api/todos — crée un élément d'agenda. */
export function createTodo(body: CreateTodo): Promise<Todo> {
  return getJson<Todo>("/api/todos", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

/** PATCH /api/todos/{id} — modifie un élément d'agenda. */
export function updateTodo(id: string, patch: UpdateTodo): Promise<Todo> {
  return getJson<Todo>(`/api/todos/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(patch),
  });
}

/** POST /api/todos/{id}/status — change le statut (pending/done/cancelled). */
export function setTodoStatus(id: string, status: TodoStatus): Promise<Todo> {
  return getJson<Todo>(`/api/todos/${encodeURIComponent(id)}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ status }),
  });
}

/** DELETE /api/todos/{id} — supprime un élément d'agenda. */
export function deleteTodo(id: string): Promise<{ id: string }> {
  return getJson<{ id: string }>(`/api/todos/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
}
