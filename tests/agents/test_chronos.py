"""CHRONOS : émissions rappel/RDV, marquage rappelé, propositions (routage HERMES/PHEME)."""

from __future__ import annotations

from jarvis.agents.chronos import Chronos, ChronosInput, ChronosOutput
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType
from jarvis.todo.models import TodoDraft, TodoKind


async def test_emits_reminder_and_marks_reminded(ctx: JarvisContext) -> None:
    todo = ctx.todos.add(TodoDraft(title="Faire les courses", date="2020-01-01"))
    out = await ctx.runner.run(Chronos(), ChronosInput(due_ids=(todo.id,)))
    assert isinstance(out, ChronosOutput)
    assert out.reminders == (todo.id,)
    assert ctx.journal.replay(types=[EventType.REMINDER_DUE])
    # marqué rappelé (dédup)
    assert ctx.todos.get(todo.id).reminded_ts is not None  # type: ignore[union-attr]


async def test_emits_appointment_upcoming(ctx: JarvisContext) -> None:
    appt = ctx.todos.add(
        TodoDraft(title="RDV kiné", date="2020-01-01", kind=TodoKind.APPOINTMENT, time="10:00")
    )
    out = await ctx.runner.run(Chronos(), ChronosInput(appointment_ids=(appt.id,)))
    assert out.appointments == (appt.id,)  # type: ignore[attr-defined]
    assert ctx.journal.replay(types=[EventType.APPOINTMENT_UPCOMING])


async def test_mail_task_proposes_via_hermes(ctx: JarvisContext) -> None:
    todo = ctx.todos.add(
        TodoDraft(title="Répondre au mail du client", date="2020-01-01", tags=("mail",))
    )
    out = await ctx.runner.run(Chronos(), ChronosInput(due_ids=(todo.id,)))
    assert isinstance(out, ChronosOutput)
    assert len(out.proposals) == 1
    assert out.proposals[0].agent == "HERMES"
    # proposition persistée sur le todo + événement émis
    assert ctx.todos.get(todo.id).proposal  # type: ignore[union-attr]
    assert ctx.journal.replay(types=[EventType.AGENT_PROPOSAL])


async def test_video_task_proposes_via_pheme(ctx: JarvisContext) -> None:
    todo = ctx.todos.add(
        TodoDraft(title="Trouver des idées de vidéos virales", date="2020-01-01", tags=("video",))
    )
    out = await ctx.runner.run(Chronos(), ChronosInput(due_ids=(todo.id,)))
    assert isinstance(out, ChronosOutput)
    assert out.proposals and out.proposals[0].agent == "PHEME"
