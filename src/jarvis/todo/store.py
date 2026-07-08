"""TodoStore — agenda persistant (tâches + rendez-vous datés, rappels).

Store dédié (ne surcharge pas `night/store.py` qui gère le travail projet DAEDALUS/VULCAN
sans dates). Même moule : sqlite partagé + verrou, WAL, modèles frozen, table additive.

Les rappels sont dédupliqués via `reminded_ts` (posé une fois émis). Le calcul de l'échéance
de rappel se fait en heure **locale naïve** (outil mono-machine) pour éviter les pièges tz.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.core.events import uuid7
from jarvis.todo.models import Todo, TodoDraft, TodoKind, TodoStatus

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS todos (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    title           TEXT NOT NULL,
    date            TEXT NOT NULL,
    time            TEXT,
    notes           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    remind_lead_min INTEGER NOT NULL DEFAULT 0,
    reminded_ts     TEXT,
    tags            TEXT NOT NULL DEFAULT '[]',
    proposal        TEXT NOT NULL DEFAULT '',
    created_ts      TEXT NOT NULL,
    updated_ts      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_todos_date ON todos(date);
"""

_UPDATABLE = frozenset(
    {"title", "date", "time", "notes", "kind", "remind_lead_min", "tags", "proposal", "status"}
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _remind_at(todo: Todo, default_hour: int) -> datetime:
    """Instant (local naïf) auquel rappeler ce todo."""
    year, month, day = (int(x) for x in todo.date.split("-"))
    if todo.time:
        hour, minute = (int(x) for x in todo.time.split(":"))
    else:
        hour, minute = default_hour, 0
    return datetime(year, month, day, hour, minute) - timedelta(minutes=todo.remind_lead_min)


class TodoStore:
    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def add(self, draft: TodoDraft) -> Todo:
        now = _now_iso()
        todo = Todo(
            id=uuid7(),
            kind=draft.kind,
            title=draft.title,
            date=draft.date,
            time=draft.time,
            notes=draft.notes,
            status=TodoStatus.PENDING,
            remind_lead_min=draft.remind_lead_min,
            tags=draft.tags,
            created_ts=now,
            updated_ts=now,
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO todos (id, kind, title, date, time, notes, status, "
                "remind_lead_min, reminded_ts, tags, proposal, created_ts, updated_ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    todo.id,
                    todo.kind.value,
                    todo.title,
                    todo.date,
                    todo.time,
                    todo.notes,
                    todo.status.value,
                    todo.remind_lead_min,
                    None,
                    json.dumps(list(todo.tags)),
                    todo.proposal,
                    todo.created_ts,
                    todo.updated_ts,
                ),
            )
            self._conn.commit()
        return todo

    def get(self, todo_id: str) -> Todo | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        return self._row_to_todo(row) if row is not None else None

    def list_by_date(self, date: str) -> list[Todo]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM todos WHERE date = ? ORDER BY time IS NULL, time, created_ts",
                (date,),
            ).fetchall()
        return [self._row_to_todo(r) for r in rows]

    def list_range(self, start: str, end: str) -> list[Todo]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM todos WHERE date BETWEEN ? AND ? ORDER BY date, time IS NULL, time",
                (start, end),
            ).fetchall()
        return [self._row_to_todo(r) for r in rows]

    def update(self, todo_id: str, **fields: object) -> Todo:
        unknown = set(fields) - _UPDATABLE
        if unknown:
            raise ValueError(f"champs non modifiables : {sorted(unknown)}")
        current = self.get(todo_id)
        if current is None:
            raise KeyError(todo_id)
        for key, value in fields.items():
            self._set_column(todo_id, key, value)
        updated = self.get(todo_id)
        assert updated is not None
        return updated

    def set_status(self, todo_id: str, status: TodoStatus) -> Todo:
        return self.update(todo_id, status=status.value)

    def set_proposal(self, todo_id: str, text: str) -> Todo:
        return self.update(todo_id, proposal=text)

    def delete(self, todo_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            self._conn.commit()

    def appointments_on(self, date: str) -> list[Todo]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM todos WHERE kind = ? AND date = ? AND status = ? "
                "ORDER BY time IS NULL, time",
                (TodoKind.APPOINTMENT.value, date, TodoStatus.PENDING.value),
            ).fetchall()
        return [self._row_to_todo(r) for r in rows]

    def due_reminders(self, now_iso: str, *, default_hour: int = 9) -> list[Todo]:
        """Todos en attente, non encore rappelés, dont l'échéance de rappel est passée."""
        now = datetime.fromisoformat(now_iso)
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM todos WHERE status = ? AND reminded_ts IS NULL",
                (TodoStatus.PENDING.value,),
            ).fetchall()
        todos = [self._row_to_todo(r) for r in rows]
        return [t for t in todos if _remind_at(t, default_hour) <= now]

    def mark_reminded(self, todo_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE todos SET reminded_ts = ?, updated_ts = ? WHERE id = ?",
                (_now_iso(), _now_iso(), todo_id),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- interne ----------------------------------------------------------
    def _set_column(self, todo_id: str, column: str, value: object) -> None:
        stored: object
        if column == "tags":
            items = list(value) if isinstance(value, (list, tuple)) else []
            stored = json.dumps(items)
        else:
            stored = value
        with self._lock:
            self._conn.execute(
                f"UPDATE todos SET {column} = ?, updated_ts = ? WHERE id = ?",
                (stored, _now_iso(), todo_id),
            )
            self._conn.commit()

    @staticmethod
    def _row_to_todo(row: sqlite3.Row) -> Todo:
        return Todo(
            id=row["id"],
            kind=TodoKind(row["kind"]),
            title=row["title"],
            date=row["date"],
            time=row["time"],
            notes=row["notes"],
            status=TodoStatus(row["status"]),
            remind_lead_min=row["remind_lead_min"],
            reminded_ts=row["reminded_ts"],
            tags=tuple(json.loads(row["tags"])),
            proposal=row["proposal"],
            created_ts=row["created_ts"],
            updated_ts=row["updated_ts"],
        )
