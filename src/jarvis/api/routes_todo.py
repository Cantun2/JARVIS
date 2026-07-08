"""Routes REST de l'agenda : tâches et rendez-vous datés (CRUD)."""

from __future__ import annotations

from calendar import monthrange

from fastapi import APIRouter, HTTPException, Request

from jarvis.api.schemas import (
    CreateTodoRequest,
    TodoDTO,
    TodoStatusRequest,
    UpdateTodoRequest,
)
from jarvis.api.views import todo_dto, todo_dtos
from jarvis.assembly import JarvisContext
from jarvis.core.events import Event, EventType
from jarvis.todo.models import TodoDraft, TodoKind, TodoStatus

router = APIRouter()


def _ctx(request: Request) -> JarvisContext:
    ctx: JarvisContext = request.app.state.ctx
    return ctx


async def _publish(ctx: JarvisContext, etype: EventType, **payload: object) -> None:
    await ctx.bus.publish(Event(type=etype, source="todo", payload=dict(payload)))


@router.get("/todos", response_model=list[TodoDTO])
async def list_todos(request: Request, date: str) -> list[TodoDTO]:
    return todo_dtos(_ctx(request).todos.list_by_date(date))


@router.get("/todos/month", response_model=list[TodoDTO])
async def list_month(request: Request, year: int, month: int) -> list[TodoDTO]:
    last = monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{last:02d}"
    return todo_dtos(_ctx(request).todos.list_range(start, end))


@router.post("/todos", response_model=TodoDTO)
async def create_todo(request: Request, body: CreateTodoRequest) -> TodoDTO:
    ctx = _ctx(request)
    todo = ctx.todos.add(
        TodoDraft(
            title=body.title,
            date=body.date,
            kind=TodoKind(body.kind),
            time=body.time,
            notes=body.notes,
            remind_lead_min=body.remind_lead_min,
            tags=tuple(body.tags),
        )
    )
    await _publish(ctx, EventType.TODO_CREATED, id=todo.id, title=todo.title, date=todo.date)
    return todo_dto(todo)


@router.patch("/todos/{todo_id}", response_model=TodoDTO)
async def update_todo(request: Request, todo_id: str, body: UpdateTodoRequest) -> TodoDTO:
    ctx = _ctx(request)
    fields = body.model_dump(exclude_none=True)
    try:
        todo = ctx.todos.update(todo_id, **fields)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Todo inconnu : {todo_id}") from exc
    await _publish(ctx, EventType.TODO_UPDATED, id=todo.id, title=todo.title, date=todo.date)
    return todo_dto(todo)


@router.post("/todos/{todo_id}/status", response_model=TodoDTO)
async def set_status(request: Request, todo_id: str, body: TodoStatusRequest) -> TodoDTO:
    ctx = _ctx(request)
    try:
        todo = ctx.todos.set_status(todo_id, TodoStatus(body.status))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Todo inconnu : {todo_id}") from exc
    await _publish(ctx, EventType.TODO_UPDATED, id=todo.id, status=todo.status.value)
    return todo_dto(todo)


@router.delete("/todos/{todo_id}")
async def delete_todo(request: Request, todo_id: str) -> dict[str, str]:
    ctx = _ctx(request)
    if ctx.todos.get(todo_id) is None:
        raise HTTPException(status_code=404, detail=f"Todo inconnu : {todo_id}")
    ctx.todos.delete(todo_id)
    await _publish(ctx, EventType.TODO_UPDATED, id=todo_id, deleted=True)
    return {"id": todo_id}
