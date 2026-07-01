"""ORACLE : compose le briefing, l'émet et le pousse sur Telegram."""

from __future__ import annotations

from jarvis.agents.oracle import BriefMail, Oracle, OracleInput, OracleOutput
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType
from jarvis.io.telegram import MockTelegram


async def test_oracle_briefing_mentions_night_report(ctx: JarvisContext) -> None:
    urgent = (BriefMail(sender="ceo@x.com", subject="Signature contrat"),)
    out = await ctx.runner.run(Oracle(), OracleInput(urgent_mails=urgent))
    assert isinstance(out, OracleOutput)
    assert "VULCAN a terminé 4" in out.text
    assert "1 mail(s) urgent(s)" in out.text
    assert "night_report" in out.sections


async def test_oracle_emits_briefing_event(ctx: JarvisContext) -> None:
    await ctx.runner.run(Oracle(), OracleInput())
    briefings = ctx.journal.replay(types=[EventType.BRIEFING_READY])
    assert len(briefings) == 1
    assert briefings[0].payload["text"].startswith("Bonjour.")


async def test_oracle_notifies_telegram(ctx: JarvisContext) -> None:
    await ctx.runner.run(Oracle(), OracleInput())
    assert isinstance(ctx.telegram, MockTelegram)
    assert len(ctx.telegram.sent) == 1
    assert ctx.telegram.sent[0].level == "info"
