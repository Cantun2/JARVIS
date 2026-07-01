"""ATLAS : la séquence de réveil complète, de bout en bout, en mock."""

from __future__ import annotations

import pytest

from jarvis.agents.atlas import Atlas, AtlasInput, AtlasOutput
from jarvis.agents.vulcan import Vulcan, VulcanInput
from jarvis.assembly import JarvisContext
from jarvis.core.errors import AgentDisarmed
from jarvis.core.events import EventType


async def test_atlas_wakeup_sequence_ordering(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Atlas(), AtlasInput(profile="deep-work"))
    assert isinstance(out, AtlasOutput)
    assert out.profile == "deep-work"
    assert out.launched >= 4 and out.opened == 3
    assert out.unplaced == 0
    assert out.briefing.startswith("Bonjour.")

    types = [e.type for e in ctx.journal.replay()]

    def idx(t: EventType) -> int:
        return types.index(t)

    # Ordre canonique de la séquence de réveil.
    assert idx(EventType.WAKE_UP) < idx(EventType.PROFILE_LOADED)
    assert idx(EventType.PROFILE_LOADED) < idx(EventType.MAIL_TRIAGED)
    assert idx(EventType.MAIL_TRIAGED) < idx(EventType.BRIEFING_READY)
    assert EventType.DESKTOP_ACTION in types


async def test_atlas_triggers_hermes_and_oracle(ctx: JarvisContext) -> None:
    await ctx.runner.run(Atlas(), AtlasInput())
    statuses = ctx.journal.latest_status_by_agent()
    assert statuses["ATLAS"]["status"] == "finished"
    assert statuses["HERMES"]["status"] == "finished"
    assert statuses["ORACLE"]["status"] == "finished"


async def test_vulcan_is_disarmed(ctx: JarvisContext) -> None:
    with pytest.raises(AgentDisarmed):
        await ctx.runner.run(Vulcan(), VulcanInput(task="ne devrait pas tourner"))
