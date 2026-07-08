"""Base des agents conversationnels (dialogue multi-tours avec mémoire).

Un agent conversationnel ne fournit qu'un `system_prompt` (sa personnalité/expertise) et,
optionnellement, un `_augment()` qui injecte du contexte (résultats web, extraits de code)
avant l'appel au modèle. La machinerie multi-tours (charge l'historique, persiste, émet les
événements `CHAT_MESSAGE`, budgette, repli déterministe) est ici, partagée.

Contrairement à ECHO (routeur vocal mono-tour), ces agents tiennent une conversation :
on **dialogue** avec eux (`contract.conversational=True`).
"""

from __future__ import annotations

import asyncio

from jarvis.agents.base import JarvisAgent
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentInput, AgentOutput
from jarvis.core.events import EventType
from jarvis.inference.gateway import InferenceGateway
from jarvis.inference.types import ChatMessage, Tier


class ConversationInput(AgentInput):
    message: str
    conversation_id: str | None = None
    project: str | None = None  # ancrage optionnel (CHIRON/NEMESIS : nom d'un dossier projet)


class ConversationOutput(AgentOutput):
    conversation_id: str
    reply: str
    turns: int


def _title_from(message: str) -> str:
    text = " ".join(message.split())
    return text[:57] + "…" if len(text) > 60 else text


def with_context(messages: list[ChatMessage], context_text: str) -> list[ChatMessage]:
    """Insère un message système de contexte juste après le prompt système principal.

    Utilisé par les experts pour injecter des résultats web (PHEME) ou des extraits de
    code (NEMESIS/CHIRON) avant l'appel au modèle.
    """
    if not context_text:
        return messages
    ctx_msg = ChatMessage(role="system", content=context_text)
    if messages and messages[0].role == "system":
        return [messages[0], ctx_msg, *messages[1:]]
    return [ctx_msg, *messages]


class ConversationalAgent(JarvisAgent):
    """Agent avec lequel on tient une conversation. Sous-classer + définir `system_prompt`."""

    system_prompt: str = ""
    _tier: Tier = "cloud"  # experts → modèle « expert » (7b) via le routage par tier
    _max_tokens: int = 700
    _reply_timeout: float = 60.0
    _history_limit: int = 20

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, ConversationInput)
        gateway = ctx.require_gateway()
        store = ctx.require_conversations()

        conv = store.get(data.conversation_id) if data.conversation_id else None
        if conv is None:
            conv = store.create(ctx.agent_name, title=_title_from(data.message))
        conv_id = conv.id

        store.append(conv_id, "user", data.message)
        await ctx.emit(
            EventType.CHAT_MESSAGE,
            conversation_id=conv_id,
            agent=ctx.agent_name,
            role="user",
            text=data.message,
        )

        messages: list[ChatMessage] = []
        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))
        messages += [
            ChatMessage(role=m.role, content=m.content)
            for m in store.history(conv_id, limit=self._history_limit)
        ]
        messages = await self._augment(messages, data, ctx)

        reply, tokens = await self._complete(gateway, messages, data)
        store.append(conv_id, "assistant", reply, tokens=tokens)
        if tokens:
            ctx.budget.charge(tokens=tokens)
        await ctx.emit(
            EventType.CHAT_MESSAGE,
            conversation_id=conv_id,
            agent=ctx.agent_name,
            role="assistant",
            text=reply,
        )
        return ConversationOutput(
            conversation_id=conv_id,
            reply=reply,
            turns=len(store.history(conv_id, limit=self._history_limit)),
        )

    async def _augment(
        self, messages: list[ChatMessage], data: ConversationInput, ctx: AgentContext
    ) -> list[ChatMessage]:
        """Hook : injecter du contexte (web, fichiers) avant l'appel. Défaut : no-op."""
        return messages

    async def _complete(
        self, gateway: InferenceGateway, messages: list[ChatMessage], data: ConversationInput
    ) -> tuple[str, int]:
        """Réponse best-effort. Repli déterministe si le modèle est lent/absent."""
        try:
            resp = await asyncio.wait_for(
                gateway.complete(messages, tier=self._tier, max_tokens=self._max_tokens),
                timeout=self._reply_timeout,
            )
        except Exception:
            return self._fallback(data), 0
        text = resp.text.strip()
        return (text or self._fallback(data)), resp.usage.total_tokens

    def _fallback(self, data: ConversationInput) -> str:
        return (
            "Je n'arrive pas à répondre tout de suite (modèle indisponible ou trop lent). "
            "Réessaie dans un instant ou reformule."
        )
