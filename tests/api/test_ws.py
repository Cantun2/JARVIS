"""WebSocket : snapshot initial puis flux d'événements live."""

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


def test_ws_sends_snapshot_then_live_events(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        snapshot = ws.receive_json()
        assert snapshot["kind"] == "snapshot"
        assert {a["name"] for a in snapshot["agents"]} >= {"ATLAS", "ORACLE"}

        # Déclenche un agent → des événements doivent arriver en live.
        client.post("/api/agents/ORACLE/run", json={})

        kinds = []
        for _ in range(3):
            msg = ws.receive_json()
            assert msg["kind"] == "event"
            kinds.append(msg["event"]["type"])
        assert "agent.started" in kinds
