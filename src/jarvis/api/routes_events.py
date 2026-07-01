"""Route REST : relecture paginée du journal d'événements."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from jarvis.api.schemas import EventDTO, EventsPageDTO
from jarvis.assembly import JarvisContext

router = APIRouter()


@router.get("/events", response_model=EventsPageDTO)
async def get_events(
    request: Request,
    since: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> EventsPageDTO:
    ctx: JarvisContext = request.app.state.ctx
    rows = ctx.journal.replay_with_seq(since_seq=since, limit=limit)
    return EventsPageDTO(
        events=[EventDTO(seq=seq, **event.to_wire()) for seq, event in rows],
        latest_seq=ctx.journal.latest_seq(),
    )
