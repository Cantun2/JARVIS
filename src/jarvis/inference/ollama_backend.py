"""Backend d'inférence Ollama (local, CPU, sans build).

Utilise l'endpoint **OpenAI-compatible** d'Ollama (`{base}/v1/chat/completions`,
`{base}/v1/models`) ; santé via l'API native `{base}/api/tags`. Aucune dépendance
nouvelle (httpx). Activé en mode `real` quand `JARVIS_OLLAMA_URL` est défini.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from jarvis.inference.types import (
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    ModelInfo,
    StreamChunk,
    Usage,
)


class OllamaBackend:
    """Client Ollama via son API OpenAI-compatible."""

    name = "ollama"

    def __init__(
        self,
        base_url: str,
        *,
        default_model: str = "qwen2.5:3b",
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout
        self._transport = transport  # injectable pour les tests (httpx.MockTransport)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        payload: dict[str, Any] = {
            "model": req.model or self._default_model,
            "messages": [m.model_dump() for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": False,
        }
        async with self._client() as client:
            resp = await client.post(f"{self._base}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return GenerateResponse(
            text=content,
            model=str(data.get("model", payload["model"])),
            backend=self.name,
            tier="local",
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
            ),
        )

    async def stream(self, req: GenerateRequest) -> AsyncIterator[StreamChunk]:
        # Phase 2 : non incrémental (une réponse). SSE token-par-token à brancher plus tard.
        resp = await self.generate(req)
        yield StreamChunk(delta=resp.text)
        yield StreamChunk(delta="", done=True)

    async def list_models(self) -> list[ModelInfo]:
        async with self._client() as client:
            resp = await client.get(f"{self._base}/v1/models")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        return [ModelInfo(id=str(m["id"]), tier="local") for m in data.get("data", [])]

    async def health(self) -> HealthStatus:
        try:
            async with self._client() as client:
                resp = await client.get(f"{self._base}/api/tags")
                resp.raise_for_status()
            return HealthStatus(ok=True, backend=self.name, detail=self._base)
        except (httpx.HTTPError, OSError) as exc:
            return HealthStatus(ok=False, backend=self.name, detail=str(exc))
