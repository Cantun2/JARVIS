"""Configuration centrale, chargée depuis l'environnement / `.env`.

En mode `mock` (défaut), aucune de ces valeurs n'est requise : tout tourne à vide.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["mock", "real"]
DesktopBackend = Literal["mock", "gnome"]
MailBackend = Literal["mock", "gmail"]


class Settings(BaseSettings):
    """Réglages du process. Les alias correspondent aux variables de `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        case_sensitive=False,
    )

    # Mode global
    mode: Mode = Field(default="mock", alias="JARVIS_MODE")

    # Serveur API
    host: str = Field(default="127.0.0.1", alias="JARVIS_HOST")
    port: int = Field(default=8000, alias="JARVIS_PORT")

    # Journal SQLite (":memory:" pour éphémère)
    db_path: str = Field(default="var/jarvis.db", alias="JARVIS_DB_PATH")

    # Inférence
    inference_url: str | None = Field(default=None, alias="JARVIS_INFERENCE_URL")
    cloud_model: str = Field(default="claude-sonnet-4-6", alias="JARVIS_CLOUD_MODEL")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    # Inférence locale (Ollama, CPU, sans build) — endpoint OpenAI-compatible :11434/v1
    ollama_url: str | None = Field(default=None, alias="JARVIS_OLLAMA_URL")
    local_model: str = Field(default="qwen2.5:3b", alias="JARVIS_LOCAL_MODEL")

    # Mails (HERMES) : mock par défaut ; gmail = OAuth Google (cf. MANUAL_SETUP)
    mail_backend: MailBackend = Field(default="mock", alias="JARVIS_MAIL_BACKEND")
    gmail_credentials_path: str | None = Field(default=None, alias="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: str | None = Field(default=None, alias="GMAIL_TOKEN_PATH")

    # Telegram
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Desktop
    desktop_backend: DesktopBackend = Field(default="mock", alias="JARVIS_DESKTOP_BACKEND")

    # Night Shift (VULCAN désarmé : simulation dry-run uniquement)
    night_shift_enabled: bool = Field(default=False, alias="JARVIS_NIGHT_SHIFT_ENABLED")
    max_usd_night: float = Field(default=5.0, alias="JARVIS_MAX_USD_NIGHT")
    max_tasks_night: int = Field(default=6, alias="JARVIS_MAX_TASKS_NIGHT")

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instance mise en cache (lecture unique de l'environnement)."""
    return Settings()
