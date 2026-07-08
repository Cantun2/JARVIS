"""Recherche web : abstraction + backends Mock (défaut), DuckDuckGo (sans clé), Keyed (clé).

Même moule que `io/mail.py` / `io/telegram.py` : Protocol + Mock (déterministe) + backends
réels (async httpx, transport injectable pour les tests) + `build_websearch(settings)`.
Best-effort : toute erreur réseau renvoie une liste vide (jamais d'exception qui casse un agent).

Gaté par `Permission.NET_WEB`. Consommé par PHEME (expert vidéo virale) et CHRONOS.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel

from jarvis.config import Settings
from jarvis.logging import get_logger

log = get_logger("jarvis.websearch")


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""


@runtime_checkable
class WebSearch(Protocol):
    name: str

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]: ...


class MockWebSearch:
    """Résultats déterministes dérivés de la requête (hors-ligne, tests stables)."""

    name = "mock"

    def __init__(self, canned: dict[str, list[SearchResult]] | None = None) -> None:
        self._canned = canned or {}

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        for key, value in self._canned.items():
            if key in query:
                return value[:limit]
        q = " ".join(query.split())
        return [
            SearchResult(
                title=f"[mock] Résultat {i + 1} — {q}",
                url=f"https://example.test/{i + 1}?q={q.replace(' ', '+')}",
                snippet=f"Extrait factice n°{i + 1} pour la requête « {q} ».",
            )
            for i in range(min(limit, 3))
        ]


class DuckDuckGoSearch:
    """Recherche sans clé via l'Instant Answer API de DuckDuckGo (résultats limités)."""

    name = "duckduckgo"

    def __init__(
        self, *, timeout: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        params = {"q": query, "format": "json", "no_html": "1", "no_redirect": "1"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.get("https://api.duckduckgo.com/", params=params)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            log.warning("websearch_failed", backend=self.name, error=str(exc))
            return []
        return self._parse(data, limit)

    @staticmethod
    def _parse(data: dict[str, Any], limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        abstract = str(data.get("AbstractText", "")).strip()
        if abstract:
            results.append(
                SearchResult(
                    title=str(data.get("Heading", "")) or abstract[:60],
                    url=str(data.get("AbstractURL", "")),
                    snippet=abstract,
                )
            )
        for topic in data.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if not isinstance(topic, dict) or "FirstURL" not in topic:
                continue
            text = str(topic.get("Text", ""))
            results.append(
                SearchResult(
                    title=text[:80] or str(topic.get("FirstURL", "")),
                    url=str(topic.get("FirstURL", "")),
                    snippet=text,
                )
            )
        return results[:limit]


class KeyedWebSearch:
    """Fournisseur générique avec clé (Brave/Serper/Tavily…) — schéma JSON générique.

    Attendu : réponse JSON avec une liste `results` d'objets `{title, url, snippet}`
    (ou `description`). Adapter au fournisseur exact le jour du branchement réel.
    """

    name = "keyed"

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.get(
                    self._url, params={"q": query, "count": limit}, headers=headers
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            log.warning("websearch_failed", backend=self.name, error=str(exc))
            return []
        out: list[SearchResult] = []
        for item in data.get("results", [])[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("snippet", item.get("description", ""))),
                )
            )
        return out


def build_websearch(settings: Settings) -> WebSearch:
    if (
        settings.mode == "real"
        and settings.web_search_provider == "keyed"
        and settings.web_search_api_key
        and settings.web_search_url
    ):
        log.info("websearch_backend", backend="keyed")
        return KeyedWebSearch(
            settings.web_search_url,
            settings.web_search_api_key,
            timeout=settings.web_search_timeout,
        )
    if settings.mode == "real" and settings.web_search_provider == "duckduckgo":
        log.info("websearch_backend", backend="duckduckgo")
        return DuckDuckGoSearch(timeout=settings.web_search_timeout)
    return MockWebSearch()
