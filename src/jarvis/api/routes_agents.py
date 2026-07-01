"""Routes REST : santé, liste des agents, déclenchement d'un agent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from jarvis import __version__
from jarvis.api.schemas import AgentDTO, HealthDTO, RunRequest, RunResultDTO
from jarvis.api.views import agent_dtos
from jarvis.assembly import JarvisContext
from jarvis.core.errors import AgentDisarmed, BudgetExceeded, PermissionDenied

router = APIRouter()


def _ctx(request: Request) -> JarvisContext:
    ctx: JarvisContext = request.app.state.ctx
    return ctx


@router.get("/health", response_model=HealthDTO)
async def health(request: Request) -> HealthDTO:
    ctx = _ctx(request)
    caps = await ctx.desktop.capabilities()
    return HealthDTO(
        mode=ctx.settings.mode,
        version=__version__,
        inference_backend=ctx.gateway.backend_name,
        desktop_backend=caps.backend,
        placement_available=caps.can_place_windows,
    )


@router.get("/agents", response_model=list[AgentDTO])
async def list_agents(request: Request) -> list[AgentDTO]:
    return agent_dtos(_ctx(request))


@router.post("/agents/{name}/run", response_model=RunResultDTO)
async def run_agent(name: str, request: Request, body: RunRequest | None = None) -> RunResultDTO:
    ctx = _ctx(request)
    if not ctx.registry.has(name):
        raise HTTPException(status_code=404, detail=f"Agent inconnu : {name}")
    agent = ctx.registry.get(name)

    raw = body.model_dump(exclude_none=True) if body else {}
    fields = agent.contract.inputs.model_fields
    payload = {k: v for k, v in raw.items() if k in fields}
    try:
        data = agent.contract.inputs(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        out = await ctx.runner.run(agent, data)
    except AgentDisarmed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except BudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    run = ctx.journal.latest_status_by_agent().get(agent.contract.name)
    return RunResultDTO(
        correlation_id=run["correlation_id"] if run else "",
        status=run["status"] if run else "finished",
        output=out.model_dump(mode="json"),
    )
