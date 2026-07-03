"""Modèle d'événement et types canoniques.

Tout ce qui se passe dans jarvis-suit est un `Event`. Les événements sont écrits
dans le journal (source de vérité, rejouable) puis diffusés sur le bus.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def uuid7() -> str:
    """UUIDv7 (préfixe temporel) → tri lexicographique ~ ordre chronologique.

    Implémentation locale (pas de dépendance) : 48 bits de timestamp ms + aléa,
    version 7 et variant RFC 4122 positionnés.
    """
    unix_ms = time.time_ns() // 1_000_000
    ts = unix_ms.to_bytes(6, "big")
    rand = bytearray(os.urandom(10))
    rand[0] = (rand[0] & 0x0F) | 0x70  # version 7
    rand[2] = (rand[2] & 0x3F) | 0x80  # variant 10xx
    return str(uuid.UUID(bytes=bytes(ts) + bytes(rand)))


def _now() -> datetime:
    return datetime.now(tz=UTC)


class EventType(StrEnum):
    """Vocabulaire d'événements. Ajouter ici avant d'émettre un nouveau type."""

    WAKE_UP = "wake_up"
    PROFILE_LOADED = "profile.loaded"
    DESKTOP_ACTION = "desktop.action"
    MAIL_RECEIVED = "mail.received"
    MAIL_TRIAGED = "mail.triaged"
    MAIL_DRAFTED = "mail.drafted"
    MAIL_RECLASSIFIED = "mail.reclassified"
    VOICE_HEARD = "voice.heard"
    VOICE_SPOKE = "voice.spoke"
    AGENT_STARTED = "agent.started"
    AGENT_FINISHED = "agent.finished"
    AGENT_FAILED = "agent.failed"
    AGENT_ESCALATED = "agent.escalated"
    BRIEFING_READY = "briefing.ready"
    BACKLOG_READY = "backlog.ready"
    TASK_TRANSITIONED = "task.transitioned"
    NIGHT_REPORT_READY = "night.report_ready"
    PERMISSION_DENIED = "permission.denied"
    BUDGET_EXCEEDED = "budget.exceeded"
    SYSTEM_HEALTH = "system.health"
    NOTIFICATION = "notification"


class Event(BaseModel):
    """Événement immuable. `payload` est libre mais documenté par type d'événement."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=uuid7)
    type: EventType
    ts: datetime = Field(default_factory=_now)
    source: str
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        """Sérialisation JSON-safe pour le WebSocket / REST."""
        return self.model_dump(mode="json")


def make_event(
    type: EventType,
    source: str,
    *,
    correlation_id: str | None = None,
    **payload: Any,
) -> Event:
    """Fabrique ergonomique : `make_event(EventType.WAKE_UP, "atlas", profile="deep-work")`."""
    return Event(
        type=type,
        source=source,
        correlation_id=correlation_id,
        payload=payload,
    )
