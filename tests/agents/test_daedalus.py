"""DAEDALUS : décomposition déterministe, persistance backlog, événement."""

from __future__ import annotations

from jarvis.agents.daedalus import Daedalus, DaedalusInput, DaedalusOutput, _decompose
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType


def test_decompose_is_deterministic() -> None:
    tasks = _decompose("Faire X")
    assert len(tasks) == 5
    assert all(t.acceptance_criteria for t in tasks)
    assert tasks == _decompose("Faire X")  # pur/déterministe


async def test_daedalus_creates_and_persists_backlog(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(
        Daedalus(), DaedalusInput(goal="Ajouter un export CSV", project_name="Reporting")
    )
    assert isinstance(out, DaedalusOutput)
    assert len(out.tasks) == 5
    project = ctx.tasks.get_project(out.project_id)
    assert project is not None and project.name == "Reporting"
    assert len(ctx.tasks.list_tasks(out.project_id)) == 5


async def test_daedalus_emits_backlog_ready(ctx: JarvisContext) -> None:
    await ctx.runner.run(Daedalus(), DaedalusInput(goal="But"))
    backlog = ctx.journal.replay(types=[EventType.BACKLOG_READY])
    assert len(backlog) == 1
    assert backlog[0].payload["count"] == 5
