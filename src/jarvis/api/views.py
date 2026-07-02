"""Construction des DTO à partir du contexte (partagé par REST et WebSocket)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from jarvis.api.schemas import (
    AgentDTO,
    BriefingDTO,
    EventDTO,
    InboxDTO,
    InboxItemDTO,
    LastRunDTO,
)
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType


def agent_dtos(ctx: JarvisContext) -> list[AgentDTO]:
    statuses = ctx.journal.latest_status_by_agent()
    out: list[AgentDTO] = []
    for contract in ctx.registry.contracts():
        run = statuses.get(contract.name)
        last = (
            LastRunDTO(
                correlation_id=run["correlation_id"],
                status=run["status"],
                tokens=run["tokens"],
                usd=run["usd"],
                ended_ts=run["ended_ts"],
                error=run["error"],
            )
            if run
            else None
        )
        out.append(
            AgentDTO(
                name=contract.name,
                mode=contract.mode,
                permissions=[p.value for p in contract.permissions],
                enabled=contract.enabled,
                status=run["status"] if run else "idle",
                last_run=last,
            )
        )
    return out


def build_snapshot(ctx: JarvisContext, *, recent: int = 100) -> dict[str, Any]:
    latest = ctx.journal.latest_seq()
    since = max(0, latest - recent)
    events = [
        EventDTO(seq=seq, **event.to_wire()).model_dump()
        for seq, event in ctx.journal.replay_with_seq(since_seq=since)
    ]
    return {
        "kind": "snapshot",
        "agents": [a.model_dump() for a in agent_dtos(ctx)],
        "events": events,
        "latest_seq": latest,
    }


def latest_inbox_dto(ctx: JarvisContext) -> InboxDTO:
    """Dernier triage HERMES, dérivé du journal (dédup par id, tri par priorité)."""
    by_id: dict[str, InboxItemDTO] = {}
    for event in ctx.journal.replay(types=[EventType.MAIL_TRIAGED]):
        p = event.payload
        mail_id = str(p.get("id", ""))
        by_id[mail_id] = InboxItemDTO(
            id=mail_id,
            sender=str(p.get("sender", "")),
            subject=str(p.get("subject", "")),
            category=str(p.get("category", "")),
            priority=int(p.get("priority", 0)),
            summary=str(p.get("summary", "")),
        )
    items = sorted(by_id.values(), key=lambda i: i.priority, reverse=True)
    counts = dict(Counter(i.category for i in items))
    return InboxDTO(items=items, counts=counts)


def latest_briefing_dto(ctx: JarvisContext) -> BriefingDTO | None:
    """Dernier briefing ORACLE, dérivé du journal."""
    briefings = ctx.journal.replay(types=[EventType.BRIEFING_READY])
    if not briefings:
        return None
    payload = briefings[-1].payload
    return BriefingDTO(
        text=str(payload.get("text", "")),
        sections=dict(payload.get("sections", {})),
    )
