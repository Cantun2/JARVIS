"""API chat : POST /api/chat crée/continue une conversation ; historique ; erreurs."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.assembly import build_context
from jarvis.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    ctx = build_context(Settings(mode="mock", db_path=":memory:", scheduler_enabled=False))
    with TestClient(create_app(ctx)) as c:
        yield c
    ctx.close()


def test_chat_creates_conversation_and_replies(client: TestClient) -> None:
    res = client.post("/api/chat", json={"agent": "JARVIS", "message": "Bonjour"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "JARVIS"
    assert body["conversation_id"]
    assert body["reply"]


def test_chat_continues_and_history_grows(client: TestClient) -> None:
    first = client.post("/api/chat", json={"agent": "JARVIS", "message": "Un"}).json()
    conv_id = first["conversation_id"]
    client.post(
        "/api/chat", json={"agent": "JARVIS", "message": "Deux", "conversation_id": conv_id}
    )
    hist = client.get(f"/api/chat/{conv_id}")
    assert hist.status_code == 200
    msgs = hist.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


def test_chat_unknown_agent_404(client: TestClient) -> None:
    res = client.post("/api/chat", json={"agent": "NOPE", "message": "x"})
    assert res.status_code == 404


def test_chat_non_conversational_agent_400(client: TestClient) -> None:
    # ATLAS n'est pas conversationnel → 400.
    res = client.post("/api/chat", json={"agent": "ATLAS", "message": "x"})
    assert res.status_code == 400


def test_unknown_conversation_history_404(client: TestClient) -> None:
    assert client.get("/api/chat/does-not-exist").status_code == 404


def test_agents_expose_conversational_flag(client: TestClient) -> None:
    agents = {a["name"]: a for a in client.get("/api/agents").json()}
    assert agents["JARVIS"]["conversational"] is True
    assert agents["ATLAS"]["conversational"] is False
