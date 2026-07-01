"""Backend d'inférence déterministe et hors-ligne (défaut en mode mock).

Aucune dépendance réseau ni modèle. Réponses reproductibles → tests stables.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal

from jarvis.inference.types import (
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    ModelInfo,
    StreamChunk,
    Usage,
)


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockBackend:
    """Renvoie un « résumé » déterministe du dernier message utilisateur."""

    name = "mock"

    def __init__(self, *, canned: dict[str, str] | None = None) -> None:
        self._canned = canned or {}

    def _respond(self, prompt: str) -> str:
        for key, value in self._canned.items():
            if key in prompt:
                return value
        one_line = " ".join(prompt.split())
        if not one_line:
            return "(vide)"
        return one_line[:117] + "…" if len(one_line) > 120 else one_line

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        text = self._respond(last_user)
        resolved: Literal["local", "cloud"] = "local" if req.tier == "auto" else req.tier
        prompt_all = "\n".join(m.content for m in req.messages)
        return GenerateResponse(
            text=text,
            model=req.model or "mock-qwen",
            backend=self.name,
            tier=resolved,
            usage=Usage(
                prompt_tokens=_approx_tokens(prompt_all),
                completion_tokens=_approx_tokens(text),
            ),
        )

    async def stream(self, req: GenerateRequest) -> AsyncIterator[StreamChunk]:
        resp = await self.generate(req)
        for word in resp.text.split():
            yield StreamChunk(delta=word + " ")
        yield StreamChunk(delta="", done=True)

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="mock-qwen", tier="local", context_length=32768)]

    async def health(self) -> HealthStatus:
        return HealthStatus(ok=True, backend=self.name, detail="déterministe, hors-ligne")
