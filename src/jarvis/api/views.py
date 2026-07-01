"""Construction des DTO à partir du contexte (partagé par REST et WebSocket)."""

from __future__ import annotations

from typing import Any

from jarvis.api.schemas import AgentDTO, EventDTO, LastRunDTO
from jarvis.assembly import JarvisContext


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
