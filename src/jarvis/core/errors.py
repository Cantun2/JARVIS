"""Exceptions du domaine. Le Core les transforme en événements traçables."""

from __future__ import annotations

from typing import Any


class JarvisError(Exception):
    """Base de toutes les erreurs métier de jarvis-suit."""


class PermissionDenied(JarvisError):
    """Un agent a demandé une permission non accordée par la policy."""


class BudgetExceeded(JarvisError):
    """Le budget (tokens / € / temps) d'un agent est dépassé."""


class AgentDisarmed(JarvisError):
    """Tentative d'exécuter un agent désarmé (ex. VULCAN, night_shift désactivé)."""


class EscalationRequired(JarvisError):
    """Un agent a besoin d'une décision humaine (UI / Telegram) avant de continuer.

    Portée par un agent pour signaler un blocage nécessitant validation.
    """

    def __init__(
        self,
        question: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(question)
        self.question = question
        self.options = options or []
        self.context = context or {}
