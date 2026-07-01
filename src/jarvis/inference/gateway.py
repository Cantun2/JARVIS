"""InferenceGateway : façade unique au-dessus d'un backend interchangeable.

Le Core ne dépend jamais d'OpenJarvis directement : il passe par cette façade.
Backend par défaut = MockBackend (déterministe, hors-ligne).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from jarvis.inference.routing import ComplexityRouter
from jarvis.inference.types import (
    ChatMessage,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    ModelInfo,
    StreamChunk,
    Tier,
)


@runtime_checkable
class InferenceBackend(Protocol):
    """Contrat d'un backend d'inférence (aligné 1:1 sur `InferenceEngine` d'OpenJarvis)."""

    name: str

    async def generate(self, req: GenerateRequest) -> GenerateResponse: ...
    def stream(self, req: GenerateRequest) -> AsyncIterator[StreamChunk]: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def health(self) -> HealthStatus: ...


class InferenceGateway:
    """Point d'entrée des agents pour l'inférence."""

    def __init__(self, backend: InferenceBackend, router: ComplexityRouter | None = None) -> None:
        self._backend = backend
        self._router = router or ComplexityRouter()

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def _prepare(
        self,
        messages: list[ChatMessage],
        *,
        tier: Tier,
        model: str | None,
        max_tokens: int,
        temperature: float,
    ) -> GenerateRequest:
        req = GenerateRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tier=tier,
        )
        # Fige le tier résolu par le routeur (auto → local|cloud).
        return req.model_copy(update={"tier": self._router.route(req)})

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        tier: Tier = "auto",
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> GenerateResponse:
        req = self._prepare(
            messages, tier=tier, model=model, max_tokens=max_tokens, temperature=temperature
        )
        return await self._backend.generate(req)

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        tier: Tier = "auto",
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamChunk]:
        req = self._prepare(
            messages, tier=tier, model=model, max_tokens=max_tokens, temperature=temperature
        )
        return self._backend.stream(req)

    async def list_models(self) -> list[ModelInfo]:
        return await self._backend.list_models()

    async def health(self) -> HealthStatus:
        return await self._backend.health()
