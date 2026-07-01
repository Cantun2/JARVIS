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

    # Telegram
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Desktop
    desktop_backend: DesktopBackend = Field(default="mock", alias="JARVIS_DESKTOP_BACKEND")

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instance mise en cache (lecture unique de l'environnement)."""
    return Settings()
