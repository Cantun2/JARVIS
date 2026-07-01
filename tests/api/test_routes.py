"""API REST : santé, agents, déclenchement, événements."""

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


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["mode"] == "mock"
    assert body["inference_backend"] == "mock"
    assert body["desktop_backend"] == "mock"
    assert body["placement_available"] is True


def test_list_agents_includes_disarmed_vulcan(client: TestClient) -> None:
    agents = {a["name"]: a for a in client.get("/api/agents").json()}
    assert {"ATLAS", "HERMES", "ORACLE", "VULCAN"} <= set(agents)
    assert agents["VULCAN"]["enabled"] is False
    assert agents["ATLAS"]["status"] == "idle"


def test_run_atlas_produces_events(client: TestClient) -> None:
    res = client.post("/api/agents/ATLAS/run", json={"profile": "deep-work"})
    assert res.status_code == 200
    assert res.json()["output"]["profile"] == "deep-work"

    events = client.get("/api/events?since=0").json()
    types = {e["type"] for e in events["events"]}
    assert {"wake_up", "profile.loaded", "briefing.ready"} <= types
    assert events["latest_seq"] > 0

    agents = {a["name"]: a for a in client.get("/api/agents").json()}
    assert agents["ATLAS"]["status"] == "finished"
    assert agents["HERMES"]["status"] == "finished"


def test_run_unknown_agent_404(client: TestClient) -> None:
    assert client.post("/api/agents/NOPE/run", json={}).status_code == 404


def test_run_vulcan_is_conflict(client: TestClient) -> None:
    assert client.post("/api/agents/VULCAN/run", json={}).status_code == 409


def test_events_pagination(client: TestClient) -> None:
    client.post("/api/agents/ORACLE/run", json={})
    page = client.get("/api/events?since=0").json()
    latest = page["latest_seq"]
    empty = client.get(f"/api/events?since={latest}").json()
    assert empty["events"] == []
