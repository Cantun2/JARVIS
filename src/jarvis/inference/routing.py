"""Routeur de complexité local ↔ cloud.

Stub Phase 1 : respecte un tier explicite ; en "auto", heuristique simple sur la
taille/nature de la requête. Point d'extension pour le routing appris d'OpenJarvis.
"""

from __future__ import annotations

from typing import Literal

from jarvis.inference.types import GenerateRequest

_CLOUD_HINTS = ("```", "refactor", "architecture", "démontre", "prouve", "planifie")


class ComplexityRouter:
    """Décide du tier (local/cloud) d'une requête."""

    def __init__(self, *, char_threshold: int = 800) -> None:
        self._threshold = char_threshold

    def route(self, req: GenerateRequest) -> Literal["local", "cloud"]:
        if req.tier != "auto":
            return req.tier
        text = "\n".join(m.content for m in req.messages)
        if len(text) > self._threshold or any(h in text.lower() for h in _CLOUD_HINTS):
            return "cloud"
        return "local"
