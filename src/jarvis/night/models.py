"""Modèles du Night Shift : Project, Task, et le Night Report (canonique)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


class TaskDraft(BaseModel):
    """Tâche proposée par DAEDALUS, avant persistance."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str = ""
    acceptance_criteria: tuple[str, ...] = ()


class Task(BaseModel):
    """Tâche persistée (snapshot immuable renvoyé par le store)."""

    model_config = ConfigDict(frozen=True)

    id: str
    project_id: str
    title: str
    description: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    status: TaskStatus = TaskStatus.BACKLOG
    report: str = ""
    diff: str = ""
    blocker: str | None = None
    created_ts: str = ""
    updated_ts: str = ""


class Project(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    goal: str
    created_ts: str = ""


class NightTask(BaseModel):
    title: str
    status: str  # done | blocked | failed
    branch: str | None = None
    note: str = ""


class NightReport(BaseModel):
    date: str
    done: int
    blocked: int
    failed: int
    cost_usd: float
    tasks: tuple[NightTask, ...] = ()
    blockers: tuple[str, ...] = ()
    dry_run: bool = False
