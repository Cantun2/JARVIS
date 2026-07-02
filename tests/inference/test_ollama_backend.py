"""OllamaBackend : conformité protocole + parsing, via transport httpx simulé."""

from __future__ import annotations

import httpx

from jarvis.inference.gateway import InferenceBackend
from jarvis.inference.ollama_backend import OllamaBackend
from jarvis.inference.types import ChatMessage, GenerateRequest


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/v1/chat/completions":
        return httpx.Response(
            200,
            json={
                "model": "qwen2.5:3b",
                "choices": [{"message": {"content": "résumé local"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    if path == "/v1/models":
        return httpx.Response(200, json={"data": [{"id": "qwen2.5:3b"}]})
    if path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})
    return httpx.Response(404)


def _backend() -> OllamaBackend:
    return OllamaBackend("http://localhost:11434", transport=httpx.MockTransport(_handler))


def test_satisfies_protocol() -> None:
    assert isinstance(_backend(), InferenceBackend)


async def test_generate_parses_response() -> None:
    resp = await _backend().generate(
        GenerateRequest(messages=[ChatMessage(role="user", content="salut")])
    )
    assert resp.text == "résumé local"
    assert resp.backend == "ollama"
    assert resp.tier == "local"
    assert resp.usage.total_tokens == 15


async def test_list_models() -> None:
    models = await _backend().list_models()
    assert [m.id for m in models] == ["qwen2.5:3b"]
    assert models[0].tier == "local"


async def test_health_ok() -> None:
    health = await _backend().health()
    assert health.ok is True
    assert health.backend == "ollama"


async def test_health_reports_failure() -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    backend = OllamaBackend("http://localhost:11434", transport=httpx.MockTransport(boom))
    health = await backend.health()
    assert health.ok is False
