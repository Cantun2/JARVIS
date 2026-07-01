// Flux d'événements temps réel via WebSocket /ws.
//
// La logique de fusion des messages est extraite dans `applyWsMessage`, une
// fonction PURE (testable sans DOM ni socket). Le hook `useEventStream` ne fait
// que gérer le cycle de vie du socket + la reconnexion à backoff exponentiel.
import { useEffect, useRef, useState } from "react";
import { wsBase } from "./api";
import type { Agent, Health, SeqEvent, WsMessage } from "./types";

/** Nombre max d'événements conservés en mémoire (flux, pas historique complet). */
export const MAX_EVENTS = 200;

export interface StreamState {
  events: SeqEvent[];
  agents: Agent[];
  latestSeq: number;
}

export const initialStreamState: StreamState = {
  events: [],
  agents: [],
  latestSeq: 0,
};

/**
 * Insère des événements dans la liste sans doublon (clé = seq), triés du plus
 * récent au plus ancien, et plafonnés à MAX_EVENTS. Idempotent : rejouer un
 * snapshot après reconnexion ne duplique rien.
 */
function mergeEvents(existing: SeqEvent[], incoming: SeqEvent[]): SeqEvent[] {
  if (incoming.length === 0) return existing;
  const bySeq = new Map<number, SeqEvent>();
  for (const ev of existing) bySeq.set(ev.seq, ev);
  for (const ev of incoming) bySeq.set(ev.seq, ev);
  return [...bySeq.values()]
    .sort((a, b) => b.seq - a.seq)
    .slice(0, MAX_EVENTS);
}

/**
 * Réduit un message WebSocket sur l'état courant. Pure et déterministe.
 * - `snapshot` : remplace les agents, fusionne les événements (dédupliqués),
 *   met à jour latestSeq (jamais en régression).
 * - `event` : fusionne l'événement unique.
 */
export function applyWsMessage(state: StreamState, msg: WsMessage): StreamState {
  switch (msg.kind) {
    case "snapshot": {
      return {
        agents: msg.agents,
        events: mergeEvents(state.events, msg.events),
        latestSeq: Math.max(state.latestSeq, msg.latest_seq),
      };
    }
    case "event": {
      const events = mergeEvents(state.events, [msg.event]);
      return {
        agents: state.agents,
        events,
        latestSeq: Math.max(state.latestSeq, msg.event.seq),
      };
    }
    default: {
      // Message inconnu : état inchangé (tolérance amont).
      return state;
    }
  }
}

/** Parse défensif d'un message brut. Retourne null si non conforme. */
export function parseWsMessage(raw: string): WsMessage | null {
  try {
    const data = JSON.parse(raw) as unknown;
    if (
      data &&
      typeof data === "object" &&
      "kind" in data &&
      ((data as { kind: unknown }).kind === "snapshot" ||
        (data as { kind: unknown }).kind === "event")
    ) {
      return data as WsMessage;
    }
    return null;
  } catch {
    return null;
  }
}

/** Délai de reconnexion à backoff exponentiel plafonné (avec jitter léger). */
export function backoffDelay(attempt: number, base = 500, max = 15000): number {
  const exp = Math.min(max, base * 2 ** attempt);
  const jitter = Math.random() * base;
  return Math.min(max, exp + jitter);
}

export interface EventStream {
  events: SeqEvent[];
  agents: Agent[];
  health: Health | null;
  connected: boolean;
}

/**
 * Hook principal : se connecte à `<base>/ws`, applique le snapshot initial puis
 * les événements, reconnecte avec backoff exponentiel, et expose l'état vivant.
 * `health` est récupéré via REST en parallèle (rafraîchi à chaque (re)connexion).
 */
export function useEventStream(base: string = ""): EventStream {
  const [state, setState] = useState<StreamState>(initialStreamState);
  const [health, setHealth] = useState<Health | null>(null);
  const [connected, setConnected] = useState(false);

  // Refs pour éviter de recréer le socket à chaque render.
  const attemptRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const closedRef = useRef(false);

  useEffect(() => {
    closedRef.current = false;
    const url = `${wsBase(base)}/ws`;

    // Récupère /api/health de façon best-effort (n'empêche jamais le WS).
    const refreshHealth = () => {
      const httpBase = base || "";
      fetch(`${httpBase}/api/health`, { headers: { Accept: "application/json" } })
        .then((r) => (r.ok ? (r.json() as Promise<Health>) : null))
        .then((h) => {
          if (!closedRef.current && h) setHealth(h);
        })
        .catch(() => {
          /* health indisponible : on n'interrompt rien */
        });
    };

    const connect = () => {
      if (closedRef.current) return;
      refreshHealth();

      let socket: WebSocket;
      try {
        socket = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        if (closedRef.current) return;
        attemptRef.current = 0;
        setConnected(true);
      };

      socket.onmessage = (ev: MessageEvent) => {
        if (closedRef.current) return;
        const msg = parseWsMessage(String(ev.data));
        if (msg) setState((prev) => applyWsMessage(prev, msg));
      };

      socket.onclose = () => {
        if (closedRef.current) return;
        setConnected(false);
        scheduleReconnect();
      };

      socket.onerror = () => {
        // onclose suivra et déclenchera la reconnexion ; on ferme proprement.
        try {
          socket.close();
        } catch {
          /* ignore */
        }
      };
    };

    const scheduleReconnect = () => {
      if (closedRef.current) return;
      const delay = backoffDelay(attemptRef.current);
      attemptRef.current += 1;
      timerRef.current = setTimeout(connect, delay);
    };

    connect();

    return () => {
      closedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      const s = socketRef.current;
      if (s) {
        s.onopen = null;
        s.onmessage = null;
        s.onclose = null;
        s.onerror = null;
        try {
          s.close();
        } catch {
          /* ignore */
        }
      }
    };
  }, [base]);

  return {
    events: state.events,
    agents: state.agents,
    health,
    connected,
  };
}
