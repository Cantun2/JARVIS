"""API Phase 4 : commande ECHO, correction de classement, brouillons."""

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


def test_echo_say_routes_to_oracle(client: TestClient) -> None:
    res = client.post("/api/echo/say", json={"utterance": "Jarvis, fais-moi le briefing"})
    assert res.status_code == 200
    body = res.json()
    assert body["wake_detected"] is True
    assert body["routed_to"] == "ORACLE"
    assert body["spoke"] is True
    assert body["response"].startswith("Bonjour.")


def test_echo_say_ignores_without_wake(client: TestClient) -> None:
    body = client.post("/api/echo/say", json={"utterance": "le briefing"}).json()
    assert body["wake_detected"] is False and body["spoke"] is False


def test_reclassify_creates_learned_rule(client: TestClient) -> None:
    # On peuple l'inbox via HERMES, puis on corrige un mail.
    client.post("/api/agents/HERMES/run")
    item = client.get("/api/inbox").json()["items"][0]
    res = client.post(f"/api/inbox/{item['id']}/reclassify", json={"category": "spam"})
    assert res.status_code == 200
    # La correction devient une règle : le prochain tri reclasse cet expéditeur.
    client.post("/api/agents/HERMES/run")
    again = next(i for i in client.get("/api/inbox").json()["items"] if i["id"] == item["id"])
    assert again["category"] == "spam"
    assert again["corrected"] is True


def test_reclassify_unknown_mail_404(client: TestClient) -> None:
    res = client.post("/api/inbox/nope/reclassify", json={"category": "info"})
    assert res.status_code == 404


def test_drafts_listed_after_triage(client: TestClient) -> None:
    assert client.get("/api/inbox/drafts").json() == []
    client.post("/api/agents/HERMES/run")
    drafts = client.get("/api/inbox/drafts").json()
    assert drafts and all(d["body"] for d in drafts)


def test_inbox_items_carry_draft(client: TestClient) -> None:
    client.post("/api/agents/HERMES/run")
    items = client.get("/api/inbox").json()["items"]
    assert any(i["draft"] for i in items if i["category"] in ("action", "urgent"))
