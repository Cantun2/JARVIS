"""WebSearch : mock déterministe, DuckDuckGo/Keyed via transport simulé, factory, gating."""

from __future__ import annotations

import httpx
import pytest

from jarvis.agents.conversational import ConversationalAgent, ConversationInput, ConversationOutput
from jarvis.assembly import JarvisContext
from jarvis.config import Settings
from jarvis.core.contracts import AgentContract, Permission
from jarvis.core.errors import PermissionDenied
from jarvis.io.websearch import (
    DuckDuckGoSearch,
    KeyedWebSearch,
    MockWebSearch,
    WebSearch,
    build_websearch,
)


def test_mock_satisfies_protocol() -> None:
    assert isinstance(MockWebSearch(), WebSearch)


async def test_mock_is_deterministic_and_limited() -> None:
    ws = MockWebSearch()
    r1 = await ws.search("vidéos virales", limit=2)
    r2 = await ws.search("vidéos virales", limit=2)
    assert [x.model_dump() for x in r1] == [x.model_dump() for x in r2]
    assert len(r1) == 2


async def test_duckduckgo_parses_instant_answer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Heading": "TikTok",
                "AbstractText": "Réseau de vidéos courtes.",
                "AbstractURL": "https://tiktok.com",
                "RelatedTopics": [
                    {"Text": "Reels Instagram", "FirstURL": "https://instagram.com/reels"},
                ],
            },
        )

    ws = DuckDuckGoSearch(transport=httpx.MockTransport(handler))
    results = await ws.search("tiktok", limit=5)
    assert results[0].url == "https://tiktok.com"
    assert any("Reels" in r.title for r in results)


async def test_duckduckgo_returns_empty_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    ws = DuckDuckGoSearch(transport=httpx.MockTransport(handler))
    assert await ws.search("x") == []


async def test_keyed_parses_generic_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={"results": [{"title": "A", "url": "https://a.test", "snippet": "sa"}]},
        )

    ws = KeyedWebSearch("https://api.test/search", "secret", transport=httpx.MockTransport(handler))
    results = await ws.search("q", limit=3)
    assert results[0].title == "A" and results[0].url == "https://a.test"


def test_build_defaults_to_mock() -> None:
    assert build_websearch(Settings(mode="mock")).name == "mock"
    assert build_websearch(Settings(mode="real", web_search_provider="mock")).name == "mock"


def test_build_selects_duckduckgo_in_real() -> None:
    ws = build_websearch(Settings(mode="real", web_search_provider="duckduckgo"))
    assert ws.name == "duckduckgo"


# --- Gating de permission via un agent jouet ---------------------------------


class _WebAgent(ConversationalAgent):
    contract = AgentContract(
        name="WEBAGENT",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE, Permission.NET_WEB),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )
    _tier = "local"

    async def _augment(self, messages, data, ctx):  # type: ignore[no-untyped-def]
        # Prouve que la capacité web est injectée quand NET_WEB est accordée.
        results = await ctx.require_web().search(data.message, limit=1)
        assert results  # MockWebSearch renvoie toujours quelque chose
        return messages


class _NoWebAgent(ConversationalAgent):
    contract = AgentContract(
        name="NOWEB",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),  # pas de NET_WEB
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )
    _tier = "local"

    async def _augment(self, messages, data, ctx):  # type: ignore[no-untyped-def]
        ctx.require_web()  # doit lever PermissionDenied
        return messages


async def test_web_injected_when_permission_granted(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(_WebAgent(), ConversationInput(message="vidéos virales sport"))
    assert isinstance(out, ConversationOutput)


async def test_web_denied_without_permission(ctx: JarvisContext) -> None:
    with pytest.raises(PermissionDenied):
        await ctx.runner.run(_NoWebAgent(), ConversationInput(message="coucou"))
