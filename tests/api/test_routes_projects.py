"""API Night Shift : projets, backlog, transitions, nuit dry-run."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.assembly import build_context
from jarvis.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    ctx = build_context(Settings(mode="mock", db_path=":memory:"))
    with TestClient(create_app(ctx)) as c:
        yield c
    ctx.close()


def _new_project(client: TestClient, goal: str = "Ajouter une page stats") -> str:
    res = client.post("/api/projects", json={"goal": goal, "name": "Web"})
    assert res.status_code == 200
    return res.json()["project"]["id"]


def test_create_project_returns_backlog(client: TestClient) -> None:
    body = client.post("/api/projects", json={"goal": "X", "name": "Web"}).json()
    assert body["project"]["name"] == "Web"
    assert len(body["tasks"]) == 5
    assert body["project"]["task_counts"]["backlog"] == 5


def test_list_projects_and_tasks(client: TestClient) -> None:
    pid = _new_project(client)
    assert any(p["id"] == pid for p in client.get("/api/projects").json())
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert len(tasks) == 5
    assert tasks[0]["acceptance_criteria"]


def test_tasks_unknown_project_404(client: TestClient) -> None:
    assert client.get("/api/projects/nope/tasks").status_code == 404


def test_transition_approve_sets_done(client: TestClient) -> None:
    pid = _new_project(client)
    tid = client.get(f"/api/projects/{pid}/tasks").json()[0]["id"]
    task = client.post(f"/api/tasks/{tid}/transition", json={"action": "approve"}).json()
    assert task["status"] == "done"


def test_transition_unknown_task_404(client: TestClient) -> None:
    assert client.post("/api/tasks/nope/transition", json={"action": "approve"}).status_code == 404


def test_night_run_and_report(client: TestClient) -> None:
    pid = _new_project(client)
    assert client.get("/api/night/report").json() is None
    report = client.post("/api/night/run", json={"project_id": pid}).json()
    assert report["dry_run"] is True
    assert report["done"] + report["blocked"] > 0
    assert client.get("/api/night/report").json()["dry_run"] is True


def test_night_run_unknown_project_404(client: TestClient) -> None:
    assert client.post("/api/night/run", json={"project_id": "nope"}).status_code == 404
