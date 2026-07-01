"""Interface Telegram : notifier l'utilisateur / escalader une décision.

Défaut = MockTelegram (aucun envoi). StubTelegram envoie réellement, mais n'est
construit que si un token est présent (opt-in). Jamais d'envoi sans token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

import httpx

from jarvis.config import Settings
from jarvis.logging import get_logger

log = get_logger("jarvis.telegram")

Level = Literal["info", "warn", "urgent"]


@dataclass
class TelegramMessage:
    text: str
    level: Level = "info"
    options: tuple[str, ...] = ()


@runtime_checkable
class TelegramNotifier(Protocol):
    async def notify(self, text: str, *, level: Level = "info") -> None: ...
    async def escalate(self, question: str, *, options: list[str] | None = None) -> str | None: ...


class MockTelegram:
    """Enregistre les messages en mémoire (assertions de test + affichage démo)."""

    def __init__(self) -> None:
        self.sent: list[TelegramMessage] = []

    async def notify(self, text: str, *, level: Level = "info") -> None:
        self.sent.append(TelegramMessage(text=text, level=level))

    async def escalate(self, question: str, *, options: list[str] | None = None) -> str | None:
        self.sent.append(
            TelegramMessage(text=question, level="urgent", options=tuple(options or ()))
        )
        return None  # pas de réponse humaine en mode mock


@dataclass
class StubTelegram:
    """Envoi réel via l'API Bot Telegram. Construit uniquement si un token existe."""

    token: str
    chat_id: str
    timeout: float = 15.0
    sent: list[TelegramMessage] = field(default_factory=list)

    async def notify(self, text: str, *, level: Level = "info") -> None:
        prefix = {"info": "ℹ️", "warn": "⚠️", "urgent": "🚨"}[level]
        self.sent.append(TelegramMessage(text=text, level=level))
        await self._send(f"{prefix} {text}")

    async def escalate(self, question: str, *, options: list[str] | None = None) -> str | None:
        opts = "\n".join(f"• {o}" for o in (options or []))
        self.sent.append(
            TelegramMessage(text=question, level="urgent", options=tuple(options or ()))
        )
        await self._send(f"🚨 Décision requise :\n{question}\n{opts}".strip())
        return None  # réponse interactive : Phase ultérieure

    async def _send(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json={"chat_id": self.chat_id, "text": text})
                resp.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            log.warning("telegram_send_failed", error=str(exc))


def build_telegram(settings: Settings) -> TelegramNotifier:
    if settings.mode == "real" and settings.telegram_bot_token and settings.telegram_chat_id:
        log.info("telegram_backend", backend="stub-real")
        return StubTelegram(settings.telegram_bot_token, settings.telegram_chat_id)
    return MockTelegram()
