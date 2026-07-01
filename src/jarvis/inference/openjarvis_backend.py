"""Backend OpenJarvis via l'API OpenAI-compatible de `jarvis serve`.

Simple client HTTP (httpx) → **aucun build Rust côté jarvis-suit**. Le build natif
ne concerne que le process serveur OpenJarvis, lancé séparément. Activé uniquement en
mode `real` avec `JARVIS_INFERENCE_URL` défini.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx

from jarvis.inference.types import (
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    ModelInfo,
    StreamChunk,
    Usage,
)


class OpenJarvisBackend:
    """Parle à un serveur OpenAI-compatible (`/v1/chat/completions`, `/v1/models`, `/health`)."""

    name = "openjarvis"

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        default_model: str = "local",
        timeout: float = 60.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._default_model = default_model
        self._timeout = timeout

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        payload: dict[str, Any] = {
            "model": req.model or self._default_model,
            "messages": [m.model_dump() for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/chat/completions", json=payload, headers=self._headers
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        resolved: Literal["local", "cloud"] = "local" if req.tier == "auto" else req.tier
        return GenerateResponse(
            text=content,
            model=str(data.get("model", payload["model"])),
            backend=self.name,
            tier=resolved,
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
            ),
        )

    async def stream(self, req: GenerateRequest) -> AsyncIterator[StreamChunk]:
        # Phase 1 : non incrémental (une seule réponse). SSE token-par-token à brancher plus tard.
        resp = await self.generate(req)
        yield StreamChunk(delta=resp.text)
        yield StreamChunk(delta="", done=True)

    async def list_models(self) -> list[ModelInfo]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/models", headers=self._headers)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        return [ModelInfo(id=str(m["id"])) for m in data.get("data", [])]

    async def health(self) -> HealthStatus:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/health", headers=self._headers)
                resp.raise_for_status()
            return HealthStatus(ok=True, backend=self.name, detail=self._base)
        except (httpx.HTTPError, OSError) as exc:
            return HealthStatus(ok=False, backend=self.name, detail=str(exc))
