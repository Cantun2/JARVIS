"""ReminderScheduler : _tick déclenche CHRONOS une fois pour un dû, dédup, no-op vide."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.assembly import JarvisContext, build_context
from jarvis.config import Settings
from jarvis.core.events import EventType
from jarvis.scheduler import ReminderScheduler
from jarvis.todo.models import TodoDraft


@pytest.fixture
def sched_ctx() -> Iterator[JarvisContext]:
    context = build_context(Settings(mode="mock", db_path=":memory:", scheduler_enabled=False))
    yield context
    context.close()


async def test_tick_runs_chronos_once_then_dedups(sched_ctx: JarvisContext) -> None:
    todo = sched_ctx.todos.add(TodoDraft(title="Tâche passée", date="2020-01-01", time="08:00"))
    scheduler = ReminderScheduler(sched_ctx)

    await scheduler._tick()
    assert sched_ctx.todos.get(todo.id).reminded_ts is not None  # type: ignore[union-attr]
    assert len(sched_ctx.journal.replay(types=[EventType.REMINDER_DUE])) == 1

    # 2e tick : le todo est déjà rappelé → due_reminders le filtre → pas de nouveau rappel.
    await scheduler._tick()
    assert len(sched_ctx.journal.replay(types=[EventType.REMINDER_DUE])) == 1


async def test_tick_noop_on_empty_agenda(sched_ctx: JarvisContext) -> None:
    scheduler = ReminderScheduler(sched_ctx)
    await scheduler._tick()
    assert sched_ctx.journal.replay(types=[EventType.REMINDER_DUE]) == []


async def test_future_todo_not_due(sched_ctx: JarvisContext) -> None:
    sched_ctx.todos.add(TodoDraft(title="Plus tard", date="2999-01-01", time="08:00"))
    scheduler = ReminderScheduler(sched_ctx)
    await scheduler._tick()
    assert sched_ctx.journal.replay(types=[EventType.REMINDER_DUE]) == []


def test_disabled_scheduler_starts_no_task(sched_ctx: JarvisContext) -> None:
    scheduler = ReminderScheduler(sched_ctx)  # settings.scheduler_enabled=False
    scheduler.start()
    assert scheduler._task is None
