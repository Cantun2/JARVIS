"""Routes REST du Night Shift : projets, backlog, transitions de tâches, nuit dry-run."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from jarvis.agents.daedalus import DaedalusInput, DaedalusOutput
from jarvis.api.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    NightReportDTO,
    ProjectDTO,
    TaskDTO,
    TransitionRequest,
)
from jarvis.api.views import (
    latest_night_report_dto,
    night_report_dto,
    project_dto,
    project_dtos,
    task_dto,
    task_dtos,
)
from jarvis.assembly import JarvisContext
from jarvis.core.events import Event, EventType
from jarvis.night.manager import NightShiftManager
from jarvis.night.models import TaskStatus

router = APIRouter()

# Action UI → statut cible.
_ACTION_TO_STATUS = {
    "approve": TaskStatus.DONE,
    "reject": TaskStatus.BACKLOG,
    "retry": TaskStatus.BACKLOG,
}


def _ctx(request: Request) -> JarvisContext:
    ctx: JarvisContext = request.app.state.ctx
    return ctx


@router.get("/projects", response_model=list[ProjectDTO])
async def list_projects(request: Request) -> list[ProjectDTO]:
    return project_dtos(_ctx(request))


@router.post("/projects", response_model=CreateProjectResponse)
async def create_project(request: Request, body: CreateProjectRequest) -> CreateProjectResponse:
    ctx = _ctx(request)
    agent = ctx.registry.get("DAEDALUS")
    data = DaedalusInput(goal=body.goal, project_name=body.name or "Projet")
    out = await ctx.runner.run(agent, data)
    assert isinstance(out, DaedalusOutput)
    project = ctx.tasks.get_project(out.project_id)
    if project is None:  # pragma: no cover — DAEDALUS vient de le créer
        raise HTTPException(status_code=500, detail="projet non créé")
    tasks = ctx.tasks.list_tasks(project.id)
    return CreateProjectResponse(
        project=project_dto(ctx, project),
        tasks=[task_dto(t) for t in tasks],
    )


@router.get("/projects/{project_id}/tasks", response_model=list[TaskDTO])
async def get_project_tasks(project_id: str, request: Request) -> list[TaskDTO]:
    ctx = _ctx(request)
    if ctx.tasks.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"projet inconnu : {project_id}")
    return task_dtos(ctx, project_id)


@router.post("/tasks/{task_id}/transition", response_model=TaskDTO)
async def transition_task(task_id: str, request: Request, body: TransitionRequest) -> TaskDTO:
    ctx = _ctx(request)
    task = ctx.tasks.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"tâche inconnue : {task_id}")
    target = _ACTION_TO_STATUS[body.action]
    updated = ctx.tasks.transition(task_id, target)
    await ctx.bus.publish(
        Event(
            type=EventType.TASK_TRANSITIONED,
            source="mission-control",
            payload={
                "task_id": task_id,
                "project_id": updated.project_id,
                "from": task.status.value,
                "to": updated.status.value,
                "action": body.action,
                "title": updated.title,
            },
        )
    )
    return task_dto(updated)


@router.post("/night/run", response_model=NightReportDTO)
async def run_night(request: Request, body: dict[str, str]) -> NightReportDTO:
    ctx = _ctx(request)
    project_id = body.get("project_id", "")
    if ctx.tasks.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"projet inconnu : {project_id}")
    manager = NightShiftManager(ctx.tasks, ctx.bus, ctx.settings)
    report = await manager.run_night(project_id)
    return night_report_dto(report)


@router.get("/night/report", response_model=NightReportDTO | None)
async def get_night_report(request: Request) -> NightReportDTO | None:
    return latest_night_report_dto(_ctx(request))
