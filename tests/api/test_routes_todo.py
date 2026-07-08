"""API agenda : création, liste (jour/mois), patch, statut, suppression + événements."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.assembly import build_context
from jarvis.config import Settings
from jarvis.core.events import EventType


@pytest.fixture
def client() -> Iterator[TestClient]:
    ctx = build_context(Settings(mode="mock", db_path=":memory:", scheduler_enabled=False))
    with TestClient(create_app(ctx)) as c:
        yield c
    ctx.close()


def _create(client: TestClient, **kw: object) -> dict:
    body = {"title": "Tâche", "date": "2026-07-08", **kw}
    res = client.post("/api/todos", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_create_and_list_by_date(client: TestClient) -> None:
    _create(client, title="Écrire")
    res = client.get("/api/todos", params={"date": "2026-07-08"})
    assert res.status_code == 200
    assert [t["title"] for t in res.json()] == ["Écrire"]


def test_month_view(client: TestClient) -> None:
    _create(client, date="2026-07-03")
    _create(client, date="2026-07-20")
    res = client.get("/api/todos/month", params={"year": 2026, "month": 7})
    assert len(res.json()) == 2


def test_patch_and_status_and_delete(client: TestClient) -> None:
    todo = _create(client)
    tid = todo["id"]
    patched = client.patch(f"/api/todos/{tid}", json={"title": "Modifié"})
    assert patched.json()["title"] == "Modifié"
    done = client.post(f"/api/todos/{tid}/status", json={"status": "done"})
    assert done.json()["status"] == "done"
    assert client.delete(f"/api/todos/{tid}").status_code == 200
    assert client.get("/api/todos", params={"date": "2026-07-08"}).json() == []


def test_patch_unknown_404(client: TestClient) -> None:
    assert client.patch("/api/todos/nope", json={"title": "x"}).status_code == 404


def test_create_emits_event(client: TestClient) -> None:
    ctx = client.app.state.ctx  # type: ignore[attr-defined]
    _create(client, title="RDV", kind="appointment", time="10:00")
    events = ctx.journal.replay(types=[EventType.TODO_CREATED])
    assert any(e.payload.get("title") == "RDV" for e in events)
