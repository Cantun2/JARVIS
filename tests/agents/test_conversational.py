"""Agent conversationnel : mémoire multi-tours, événements CHAT_MESSAGE, repli, gating."""

from __future__ import annotations

import pytest

from jarvis.agents.conversational import ConversationalAgent, ConversationInput, ConversationOutput
from jarvis.agents.jarvis import Jarvis
from jarvis.assembly import JarvisContext
from jarvis.core.contracts import AgentContract, Budget, Permission
from jarvis.core.errors import PermissionDenied
from jarvis.core.events import EventType


class _Stub(ConversationalAgent):
    contract = AgentContract(
        name="STUB",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),
        budget=Budget(max_tokens_day=10_000, max_runtime_min=1),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )
    system_prompt = "Tu es un agent de test."
    _tier = "local"  # mock déterministe


class _NoInference(ConversationalAgent):
    contract = AgentContract(
        name="NOINF",
        mode="on_demand",
        permissions=(),  # pas de NET_CLOUD_INFERENCE → require_gateway lève
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )


async def test_reply_persisted_and_two_events(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(_Stub(), ConversationInput(message="Bonjour"))
    assert isinstance(out, ConversationOutput)
    assert out.reply  # non vide (mock renvoie un écho déterministe)
    # 2 messages persistés (user + assistant)
    hist = ctx.conversations.history(out.conversation_id)
    assert [m.role for m in hist] == ["user", "assistant"]
    # 2 événements CHAT_MESSAGE émis
    chat_events = ctx.journal.replay(types=[EventType.CHAT_MESSAGE])
    roles = [e.payload["role"] for e in chat_events]
    assert roles == ["user", "assistant"]


async def test_conversation_is_continued(ctx: JarvisContext) -> None:
    first = await ctx.runner.run(_Stub(), ConversationInput(message="Un"))
    second = await ctx.runner.run(
        _Stub(), ConversationInput(message="Deux", conversation_id=first.conversation_id)
    )
    assert second.conversation_id == first.conversation_id
    hist = ctx.conversations.history(first.conversation_id)
    # 4 tours : user "Un", assistant, user "Deux", assistant
    assert len(hist) == 4
    assert [m.role for m in hist] == ["user", "assistant", "user", "assistant"]
    assert hist[0].content == "Un" and hist[2].content == "Deux"


async def test_requires_inference_permission(ctx: JarvisContext) -> None:
    with pytest.raises(PermissionDenied):
        await ctx.runner.run(_NoInference(), ConversationInput(message="Coucou"))


async def test_jarvis_is_conversational_and_replies(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Jarvis(), ConversationInput(message="Qui es-tu ?"))
    assert isinstance(out, ConversationOutput)
    assert Jarvis().contract.conversational is True
    assert out.turns == 2
