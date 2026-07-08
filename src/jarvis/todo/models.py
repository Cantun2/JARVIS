"""Modèles de l'agenda : Todo (tâche ou rendez-vous), statut, brouillon de création."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TodoKind(StrEnum):
    TASK = "task"  # chose à faire (peut être sans heure)
    APPOINTMENT = "appointment"  # rendez-vous (généralement avec heure)


class TodoStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class TodoDraft(BaseModel):
    """Todo proposé (création), avant persistance."""

    model_config = ConfigDict(frozen=True)

    title: str
    date: str  # 'YYYY-MM-DD'
    kind: TodoKind = TodoKind.TASK
    time: str | None = None  # 'HH:MM' ou None (tâche sans heure)
    notes: str = ""
    remind_lead_min: int = 0  # minutes avant l'échéance pour rappeler
    tags: tuple[str, ...] = ()


class Todo(BaseModel):
    """Todo persisté (snapshot immuable renvoyé par le store)."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: TodoKind
    title: str
    date: str
    time: str | None = None
    notes: str = ""
    status: TodoStatus = TodoStatus.PENDING
    remind_lead_min: int = 0
    reminded_ts: str | None = None  # posé une fois le rappel émis (dédup)
    tags: tuple[str, ...] = ()
    proposal: str = ""  # suggestion écrite par CHRONOS
    created_ts: str = ""
    updated_ts: str = ""
