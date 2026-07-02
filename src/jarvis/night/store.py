"""TaskStore — état mutable des projets/tâches (projection SQLite).

Même moule que `core/journal.py` (connexion partagée + verrou). Le journal reste la
trace événementielle (ADR-4) ; ce store porte l'état courant projetable pour l'UI.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from jarvis.core.events import uuid7
from jarvis.night.models import (
    NightReport,
    Project,
    Task,
    TaskDraft,
    TaskStatus,
)

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS projects (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    goal       TEXT NOT NULL,
    created_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    acceptance_criteria TEXT NOT NULL DEFAULT '[]',
    status              TEXT NOT NULL DEFAULT 'backlog',
    report              TEXT NOT NULL DEFAULT '',
    diff                TEXT NOT NULL DEFAULT '',
    blocker             TEXT,
    created_ts          TEXT NOT NULL,
    updated_ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tasks_project ON tasks(project_id);

CREATE TABLE IF NOT EXISTS night_reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    created_ts TEXT NOT NULL,
    payload    TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class TaskStore:
    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # --- Projets -----------------------------------------------------------
    def create_project(self, name: str, goal: str) -> Project:
        project = Project(id=uuid7(), name=name, goal=goal, created_ts=_now_iso())
        with self._lock:
            self._conn.execute(
                "INSERT INTO projects (id, name, goal, created_ts) VALUES (?, ?, ?, ?)",
                (project.id, project.name, project.goal, project.created_ts),
            )
            self._conn.commit()
        return project

    def list_projects(self) -> list[Project]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM projects ORDER BY created_ts").fetchall()
        return [
            Project(id=r["id"], name=r["name"], goal=r["goal"], created_ts=r["created_ts"])
            for r in rows
        ]

    def get_project(self, project_id: str) -> Project | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            return None
        return Project(
            id=row["id"], name=row["name"], goal=row["goal"], created_ts=row["created_ts"]
        )

    # --- Tâches ------------------------------------------------------------
    def add_tasks(self, project_id: str, drafts: list[TaskDraft]) -> list[Task]:
        tasks: list[Task] = []
        now = _now_iso()
        with self._lock:
            for draft in drafts:
                task = Task(
                    id=uuid7(),
                    project_id=project_id,
                    title=draft.title,
                    description=draft.description,
                    acceptance_criteria=draft.acceptance_criteria,
                    status=TaskStatus.BACKLOG,
                    created_ts=now,
                    updated_ts=now,
                )
                self._conn.execute(
                    "INSERT INTO tasks (id, project_id, title, description, acceptance_criteria, "
                    "status, report, diff, blocker, created_ts, updated_ts) "
                    "VALUES (?, ?, ?, ?, ?, ?, '', '', NULL, ?, ?)",
                    (
                        task.id,
                        project_id,
                        task.title,
                        task.description,
                        json.dumps(list(task.acceptance_criteria)),
                        task.status.value,
                        now,
                        now,
                    ),
                )
                tasks.append(task)
            self._conn.commit()
        return tasks

    def list_tasks(self, project_id: str) -> list[Task]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY rowid", (project_id,)
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_task(self, task_id: str) -> Task | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row is not None else None

    def transition(
        self,
        task_id: str,
        to: TaskStatus,
        *,
        report: str | None = None,
        diff: str | None = None,
        blocker: str | None = None,
    ) -> Task:
        with self._lock:
            row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(f"Tâche inconnue : {task_id}")
            new_report = row["report"] if report is None else report
            new_diff = row["diff"] if diff is None else diff
            new_blocker = blocker if to == TaskStatus.BLOCKED else None
            self._conn.execute(
                "UPDATE tasks SET status=?, report=?, diff=?, blocker=?, updated_ts=? WHERE id=?",
                (to.value, new_report, new_diff, new_blocker, _now_iso(), task_id),
            )
            self._conn.commit()
            updated = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(updated)

    def task_counts(self, project_id: str) -> dict[str, int]:
        counts = {s.value: 0 for s in TaskStatus}
        with self._lock:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks WHERE project_id = ? GROUP BY status",
                (project_id,),
            ).fetchall()
        for r in rows:
            counts[r["status"]] = int(r["n"])
        return counts

    # --- Night Report ------------------------------------------------------
    def save_night_report(self, project_id: str | None, report: NightReport) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO night_reports (project_id, created_ts, payload) VALUES (?, ?, ?)",
                (project_id, _now_iso(), report.model_dump_json()),
            )
            self._conn.commit()

    def latest_night_report(self) -> NightReport | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM night_reports ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return NightReport.model_validate_json(row["payload"])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            acceptance_criteria=tuple(json.loads(row["acceptance_criteria"])),
            status=TaskStatus(row["status"]),
            report=row["report"],
            diff=row["diff"],
            blocker=row["blocker"],
            created_ts=row["created_ts"],
            updated_ts=row["updated_ts"],
        )
