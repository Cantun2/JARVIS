"""Journal SQLite (WAL) — source de vérité, rejouable.

`append` est appelé par le bus AVANT tout fan-out : même si un handler plante,
l'événement est déjà durable. `replay` relit dans l'ordre total (`seq`).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jarvis.core.events import Event, EventType

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS events (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    id             TEXT UNIQUE NOT NULL,
    type           TEXT NOT NULL,
    ts             TEXT NOT NULL,
    source         TEXT NOT NULL,
    correlation_id TEXT,
    payload        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(type);
CREATE INDEX IF NOT EXISTS ix_events_corr ON events(correlation_id);

CREATE TABLE IF NOT EXISTS agent_runs (
    correlation_id TEXT PRIMARY KEY,
    agent          TEXT NOT NULL,
    status         TEXT NOT NULL,
    started_ts     TEXT NOT NULL,
    ended_ts       TEXT,
    tokens         INTEGER NOT NULL DEFAULT 0,
    usd            REAL NOT NULL DEFAULT 0,
    error          TEXT
);
CREATE INDEX IF NOT EXISTS ix_runs_agent ON agent_runs(agent);
"""


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class SQLiteJournal:
    """Journal append-only + vue matérialisée du cycle de vie des agents."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False + verrou : sûr avec l'event loop et le threadpool ASGI.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # --- Événements --------------------------------------------------------
    def append(self, event: Event) -> int:
        """Persiste un événement, retourne son `seq` (ordre total)."""
        wire = event.to_wire()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (id, type, ts, source, correlation_id, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    wire["id"],
                    wire["type"],
                    wire["ts"],
                    wire["source"],
                    wire["correlation_id"],
                    json.dumps(wire["payload"]),
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid or 0)

    def replay_with_seq(
        self,
        *,
        since_seq: int = 0,
        types: Iterable[EventType] | None = None,
        limit: int | None = None,
    ) -> list[tuple[int, Event]]:
        """Comme `replay`, mais renvoie aussi le `seq` de chaque événement."""
        sql = "SELECT * FROM events WHERE seq > ?"
        params: list[Any] = [since_seq]
        if types is not None:
            type_values = [t.value for t in types]
            if not type_values:
                return []
            placeholders = ",".join("?" for _ in type_values)
            sql += f" AND type IN ({placeholders})"
            params.extend(type_values)
        sql += " ORDER BY seq ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [(int(r["seq"]), self._row_to_event(r)) for r in rows]

    def replay(
        self,
        *,
        since_seq: int = 0,
        types: Iterable[EventType] | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Relit les événements de `seq > since_seq`, dans l'ordre."""
        return [
            event
            for _seq, event in self.replay_with_seq(since_seq=since_seq, types=types, limit=limit)
        ]

    def latest_seq(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) AS s FROM events").fetchone()
        return int(row["s"])

    def seq_of(self, event_id: str) -> int | None:
        with self._lock:
            row = self._conn.execute("SELECT seq FROM events WHERE id = ?", (event_id,)).fetchone()
        return int(row["seq"]) if row else None

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event.model_validate(
            {
                "id": row["id"],
                "type": row["type"],
                "ts": row["ts"],
                "source": row["source"],
                "correlation_id": row["correlation_id"],
                "payload": json.loads(row["payload"]),
            }
        )

    # --- Cycle de vie des agents ------------------------------------------
    def record_run_start(self, correlation_id: str, agent: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO agent_runs (correlation_id, agent, status, started_ts) "
                "VALUES (?, ?, 'started', ?) "
                "ON CONFLICT(correlation_id) DO UPDATE SET "
                "status='started', started_ts=excluded.started_ts",
                (correlation_id, agent, _now_iso()),
            )
            self._conn.commit()

    def record_run_end(
        self,
        correlation_id: str,
        status: str,
        *,
        tokens: int = 0,
        usd: float = 0.0,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE agent_runs SET status=?, ended_ts=?, tokens=?, usd=?, error=? "
                "WHERE correlation_id=?",
                (status, _now_iso(), tokens, usd, error, correlation_id),
            )
            self._conn.commit()

    def latest_status_by_agent(self) -> dict[str, dict[str, Any]]:
        """Dernier run connu par agent (pour le panneau statut de l'UI).

        Ordonné par `rowid` (ordre d'insertion) → déterministe même si deux runs
        partagent le même timestamp.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT r.* FROM agent_runs r "
                "JOIN (SELECT agent, MAX(rowid) AS m FROM agent_runs GROUP BY agent) g "
                "ON r.agent=g.agent AND r.rowid=g.m"
            ).fetchall()
        return {r["agent"]: dict(r) for r in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
