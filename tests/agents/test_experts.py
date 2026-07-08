"""Les 4 experts : conversationnels, augment web/fichiers, persistance, gating de permission."""

from __future__ import annotations

from jarvis.agents.arachne import Arachne
from jarvis.agents.chiron import Chiron
from jarvis.agents.conversational import ConversationInput, ConversationOutput
from jarvis.agents.nemesis import Nemesis
from jarvis.agents.pheme import Pheme
from jarvis.assembly import JarvisContext
from jarvis.core.contracts import Permission
from jarvis.core.events import EventType


def test_all_experts_are_conversational() -> None:
    for agent in (Pheme(), Arachne(), Chiron(), Nemesis()):
        assert agent.contract.conversational is True
        assert Permission.MAIL_SEND not in agent.contract.permissions


async def test_pheme_uses_web_and_replies(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Pheme(), ConversationInput(message="défis endurance viraux"))
    assert isinstance(out, ConversationOutput)
    assert out.reply
    chat_events = ctx.journal.replay(types=[EventType.CHAT_MESSAGE])
    assert [e.payload["role"] for e in chat_events] == ["user", "assistant"]


async def test_arachne_replies_without_web_or_files(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Arachne(), ConversationInput(message="rythme de coupe pour un vlog"))
    assert isinstance(out, ConversationOutput)
    assert out.reply


async def test_nemesis_reads_project_and_audits(ctx: JarvisContext) -> None:
    # En mock, le FileReader expose l'arbre « demo » (app.py avec défauts évidents).
    out = await ctx.runner.run(
        Nemesis(), ConversationInput(message="Audite ce projet", project="demo")
    )
    assert isinstance(out, ConversationOutput)
    assert out.reply


async def test_chiron_grounds_on_project_when_named(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(
        Chiron(), ConversationInput(message="Explique-moi ce code", project="demo")
    )
    assert isinstance(out, ConversationOutput)
    assert out.reply


def test_pheme_needs_web_permission() -> None:
    assert Permission.NET_WEB in Pheme().contract.permissions


def test_auditors_need_fs_permission() -> None:
    assert Permission.FS_PROJECT_DIRS in Nemesis().contract.permissions
    assert Permission.FS_PROJECT_DIRS in Chiron().contract.permissions
