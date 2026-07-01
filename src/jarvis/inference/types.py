"""Types d'échange de la couche d'inférence (alignés sur l'API OpenAI/OpenJarvis)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["system", "user", "assistant"]
Tier = Literal["local", "cloud", "auto"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role
    content: str


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class GenerateRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    max_tokens: int = 512
    temperature: float = 0.2
    tier: Tier = "auto"


class GenerateResponse(BaseModel):
    text: str
    model: str
    backend: str
    tier: Literal["local", "cloud"]
    usage: Usage = Usage()


class StreamChunk(BaseModel):
    delta: str
    done: bool = False


class ModelInfo(BaseModel):
    id: str
    tier: Literal["local", "cloud"] = "local"
    context_length: int | None = None


class HealthStatus(BaseModel):
    ok: bool
    backend: str
    detail: str = ""
