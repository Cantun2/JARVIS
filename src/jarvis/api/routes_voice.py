"""Routes REST Phase 4 : ECHO (commande parlée), brouillons et correction de classement."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from jarvis.agents.echo import Echo, EchoInput, EchoOutput
from jarvis.api.schemas import (
    DraftDTO,
    EchoRequest,
    EchoResponseDTO,
    ReclassifyRequest,
)
from jarvis.api.views import drafts_dtos, latest_inbox_dto
from jarvis.assembly import JarvisContext
from jarvis.core.errors import PermissionDenied
from jarvis.core.events import Event, EventType

router = APIRouter()


def _ctx(request: Request) -> JarvisContext:
    ctx: JarvisContext = request.app.state.ctx
    return ctx


@router.post("/echo/say", response_model=EchoResponseDTO)
async def echo_say(request: Request, body: EchoRequest) -> EchoResponseDTO:
    """Simule une commande « parlée » : exécute ECHO avec le transcript fourni."""
    ctx = _ctx(request)
    try:
        out = await ctx.runner.run(Echo(), EchoInput(utterance=body.utterance))
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    assert isinstance(out, EchoOutput)
    return EchoResponseDTO(
        heard=out.heard,
        wake_detected=out.wake_detected,
        intent=out.intent,
        routed_to=out.routed_to,
        response=out.response,
        spoke=out.spoke,
    )


@router.post("/inbox/{mail_id}/reclassify")
async def reclassify(request: Request, mail_id: str, body: ReclassifyRequest) -> dict[str, str]:
    """Corrige la catégorie d'un mail → règle apprise (expéditeur → catégorie)."""
    ctx = _ctx(request)
    inbox = latest_inbox_dto(ctx)
    item = next((i for i in inbox.items if i.id == mail_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Mail inconnu : {mail_id}")
    ctx.mail_memory.set_override(item.sender, body.category)
    await ctx.bus.publish(
        Event(
            type=EventType.MAIL_RECLASSIFIED,
            source="inbox",
            payload={"id": mail_id, "sender": item.sender, "category": body.category},
        )
    )
    return {"id": mail_id, "sender": item.sender, "category": body.category}


@router.get("/inbox/drafts", response_model=list[DraftDTO])
async def list_drafts(request: Request) -> list[DraftDTO]:
    return drafts_dtos(_ctx(request))
