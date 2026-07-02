"""TaskStore : CRUD projets/tâches, transitions, compteurs, night report."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.night.models import NightReport, NightTask, TaskDraft, TaskStatus
from jarvis.night.store import TaskStore


@pytest.fixture
def store() -> Iterator[TaskStore]:
    s = TaskStore(":memory:")
    yield s
    s.close()


def test_create_project_and_list(store: TaskStore) -> None:
    p = store.create_project("Demo", "Objectif")
    assert p.id and p.created_ts
    assert [pr.id for pr in store.list_projects()] == [p.id]
    assert store.get_project(p.id) is not None


def test_add_tasks_and_list_order(store: TaskStore) -> None:
    p = store.create_project("Demo", "But")
    tasks = store.add_tasks(
        p.id,
        [TaskDraft(title="A", acceptance_criteria=("c1", "c2")), TaskDraft(title="B")],
    )
    assert [t.title for t in tasks] == ["A", "B"]
    listed = store.list_tasks(p.id)
    assert [t.title for t in listed] == ["A", "B"]
    assert listed[0].acceptance_criteria == ("c1", "c2")
    assert all(t.status == TaskStatus.BACKLOG for t in listed)


def test_transition_updates_status_and_fields(store: TaskStore) -> None:
    p = store.create_project("Demo", "But")
    (task,) = store.add_tasks(p.id, [TaskDraft(title="A")])
    updated = store.transition(task.id, TaskStatus.REVIEW, report="ok", diff="+x")
    assert updated.status == TaskStatus.REVIEW
    assert updated.report == "ok" and updated.diff == "+x"
    assert updated.updated_ts >= task.updated_ts


def test_transition_blocked_records_blocker(store: TaskStore) -> None:
    p = store.create_project("Demo", "But")
    (task,) = store.add_tasks(p.id, [TaskDraft(title="A")])
    blocked = store.transition(task.id, TaskStatus.BLOCKED, blocker="quelle archi ?")
    assert blocked.status == TaskStatus.BLOCKED
    assert blocked.blocker == "quelle archi ?"


def test_transition_unknown_task_raises(store: TaskStore) -> None:
    with pytest.raises(KeyError):
        store.transition("nope", TaskStatus.DONE)


def test_task_counts(store: TaskStore) -> None:
    p = store.create_project("Demo", "But")
    tasks = store.add_tasks(p.id, [TaskDraft(title=f"T{i}") for i in range(3)])
    store.transition(tasks[0].id, TaskStatus.DONE)
    counts = store.task_counts(p.id)
    assert counts["done"] == 1 and counts["backlog"] == 2


def test_night_report_roundtrip(store: TaskStore) -> None:
    assert store.latest_night_report() is None
    report = NightReport(
        date="2026-07-02",
        done=2,
        blocked=1,
        failed=0,
        cost_usd=0.1,
        tasks=(NightTask(title="A", status="done"),),
        blockers=("q?",),
        dry_run=True,
    )
    store.save_night_report("proj", report)
    latest = store.latest_night_report()
    assert latest is not None and latest.done == 2 and latest.dry_run is True
