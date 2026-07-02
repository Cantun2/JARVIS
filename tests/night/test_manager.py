"""NightShiftManager : simulation dry-run, budgets, événements, zéro exécution réelle."""

from __future__ import annotations

import asyncio
import os
import subprocess

import pytest

from jarvis.assembly import JarvisContext, build_context
from jarvis.config import Settings
from jarvis.core.events import EventType
from jarvis.night.manager import NightShiftManager
from jarvis.night.models import TaskDraft


def _ctx(**overrides: object) -> JarvisContext:
    return build_context(Settings(mode="mock", db_path=":memory:", **overrides))


def _seed(ctx: JarvisContext, n: int) -> str:
    project = ctx.tasks.create_project("Demo", "But")
    ctx.tasks.add_tasks(project.id, [TaskDraft(title=f"T{i}") for i in range(n)])
    return project.id


async def test_run_night_progresses_and_reports() -> None:
    ctx = _ctx()
    pid = _seed(ctx, 5)
    report = await NightShiftManager(ctx.tasks, ctx.bus, ctx.settings).run_night(pid)
    await ctx.bus.drain()
    assert report.dry_run is True
    assert report.done + report.blocked == 5
    counts = ctx.tasks.task_counts(pid)
    assert counts["review"] == report.done
    assert counts["blocked"] == report.blocked
    types = [e.type for e in ctx.journal.replay()]
    assert EventType.NIGHT_REPORT_READY in types
    assert types.count(EventType.TASK_TRANSITIONED) == 10  # 5 tâches × 2 transitions
    ctx.close()


async def test_respects_max_tasks_night() -> None:
    ctx = _ctx(max_tasks_night=2)
    pid = _seed(ctx, 5)
    report = await NightShiftManager(ctx.tasks, ctx.bus, ctx.settings).run_night(pid)
    assert report.done + report.blocked == 2
    assert ctx.tasks.task_counts(pid)["backlog"] == 3
    ctx.close()


async def test_respects_max_usd_night() -> None:
    ctx = _ctx(max_usd_night=0.1)  # 0.05/tâche → 2 tâches
    pid = _seed(ctx, 5)
    report = await NightShiftManager(ctx.tasks, ctx.bus, ctx.settings).run_night(pid)
    assert report.cost_usd <= 0.1
    assert report.done + report.blocked == 2
    ctx.close()


async def test_no_shell_or_git_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garde-fou : la nuit dry-run ne doit invoquer aucun process."""

    def boom(*_a: object, **_k: object) -> object:
        raise AssertionError("exécution de process interdite en dry-run")

    async def aboom(*_a: object, **_k: object) -> object:
        raise AssertionError("subprocess async interdit en dry-run")

    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(os, "system", boom)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", aboom)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", aboom)

    ctx = _ctx()
    pid = _seed(ctx, 4)
    report = await NightShiftManager(ctx.tasks, ctx.bus, ctx.settings).run_night(pid)
    assert report.dry_run is True
    ctx.close()
