"""Modèles du sous-système de conversation (frozen, comme night/models)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

ChatRole = Literal["system", "user", "assistant"]


class Conversation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    agent: str  # nom de l'agent interlocuteur (ex. "JARVIS", "NEMESIS")
    title: str = ""
    created_ts: str = ""
    updated_ts: str = ""


class ConvMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    conversation_id: str
    role: ChatRole
    content: str
    tokens: int = 0
    created_ts: str = ""
