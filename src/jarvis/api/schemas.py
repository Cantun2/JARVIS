"""DTO REST/WS — séparés des modèles internes (contrat de câble stable avec l'UI)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthDTO(BaseModel):
    mode: str
    version: str
    inference_backend: str
    desktop_backend: str
    placement_available: bool


class LastRunDTO(BaseModel):
    correlation_id: str
    status: str
    tokens: int
    usd: float
    ended_ts: str | None = None
    error: str | None = None


class AgentDTO(BaseModel):
    name: str
    mode: str
    permissions: list[str]
    enabled: bool
    status: str  # idle | started | finished | failed | escalated
    last_run: LastRunDTO | None = None


class RunRequest(BaseModel):
    profile: str | None = None


class RunResultDTO(BaseModel):
    correlation_id: str
    status: str
    output: dict[str, Any]


class EventDTO(BaseModel):
    seq: int
    id: str
    type: str
    ts: str
    source: str
    correlation_id: str | None = None
    payload: dict[str, Any]


class EventsPageDTO(BaseModel):
    events: list[EventDTO]
    latest_seq: int
