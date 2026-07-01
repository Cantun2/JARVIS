"""Gateway + MockBackend : déterminisme, routing local/cloud, streaming."""

from __future__ import annotations

from jarvis.inference.gateway import InferenceBackend, InferenceGateway
from jarvis.inference.mock_backend import MockBackend
from jarvis.inference.routing import ComplexityRouter
from jarvis.inference.types import ChatMessage, GenerateRequest


def _msg(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


def test_mock_backend_satisfies_protocol() -> None:
    assert isinstance(MockBackend(), InferenceBackend)


async def test_complete_is_deterministic() -> None:
    gw = InferenceGateway(MockBackend())
    r1 = await gw.complete([_msg("Bonjour JARVIS")])
    r2 = await gw.complete([_msg("Bonjour JARVIS")])
    assert r1.text == r2.text == "Bonjour JARVIS"
    assert r1.backend == "mock"
    assert r1.usage.total_tokens > 0


async def test_canned_response_matches_substring() -> None:
    gw = InferenceGateway(MockBackend(canned={"facture": "action_requise"}))
    r = await gw.complete([_msg("Rappel: votre facture est en attente")])
    assert r.text == "action_requise"


def test_router_auto_picks_cloud_for_code_or_long_text() -> None:
    router = ComplexityRouter()
    assert router.route(GenerateRequest(messages=[_msg("```py\nx=1\n```")])) == "cloud"
    assert router.route(GenerateRequest(messages=[_msg("salut")])) == "local"
    assert router.route(GenerateRequest(messages=[_msg("x" * 900)])) == "cloud"


def test_router_respects_explicit_tier() -> None:
    router = ComplexityRouter()
    assert router.route(GenerateRequest(messages=[_msg("salut")], tier="cloud")) == "cloud"


async def test_resolved_tier_is_recorded_in_response() -> None:
    gw = InferenceGateway(MockBackend())
    resp = await gw.complete([_msg("```code```")], tier="auto")
    assert resp.tier == "cloud"


async def test_stream_yields_chunks_then_done() -> None:
    gw = InferenceGateway(MockBackend())
    chunks = [c async for c in gw.stream([_msg("un deux trois")])]
    assert chunks[-1].done is True
    assert "".join(c.delta for c in chunks).strip() == "un deux trois"
