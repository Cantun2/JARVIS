"""HERMES : classification déterministe, événements, budget chargé."""

from __future__ import annotations

from jarvis.agents.hermes import Hermes, HermesInput, HermesOutput, _fallback_summary, classify
from jarvis.agents.mocks.mail_fixtures import MOCK_MAILS
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType
from jarvis.io.mail import Mail


def _mail(mail_id: str):  # type: ignore[no-untyped-def]
    return next(m for m in MOCK_MAILS if m.id == mail_id)


def test_classification_rules() -> None:
    assert classify(_mail("m1"))[0] == "urgent"  # CEO VIP + "avant 12h"
    assert classify(_mail("m3"))[0] == "action"  # "pouvez-vous ... ?"
    assert classify(_mail("m8"))[0] == "newsletter"
    assert classify(_mail("m9"))[0] == "spam"


async def test_hermes_emits_and_triages_all(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Hermes(), HermesInput())
    assert isinstance(out, HermesOutput)
    assert len(out.triaged) == len(MOCK_MAILS)

    received = ctx.journal.replay(types=[EventType.MAIL_RECEIVED])
    triaged = ctx.journal.replay(types=[EventType.MAIL_TRIAGED])
    assert len(received) == len(MOCK_MAILS)
    assert len(triaged) == len(MOCK_MAILS)


async def test_hermes_output_sorted_and_counted(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Hermes(), HermesInput())
    assert isinstance(out, HermesOutput)
    priorities = [m.priority for m in out.triaged]
    assert priorities == sorted(priorities, reverse=True)  # trié par priorité
    assert out.counts.get("urgent", 0) >= 2  # m1 + m2
    assert len(out.urgent) == out.counts["urgent"]


async def test_hermes_charges_token_budget(ctx: JarvisContext) -> None:
    await ctx.runner.run(Hermes(), HermesInput())
    status = ctx.journal.latest_status_by_agent()["HERMES"]
    assert status["status"] == "finished"
    assert status["tokens"] > 0  # le résumé via gateway a consommé des tokens


async def test_triaged_event_is_enriched(ctx: JarvisContext) -> None:
    await ctx.runner.run(Hermes(), HermesInput())
    triaged = ctx.journal.replay(types=[EventType.MAIL_TRIAGED])
    payload = triaged[0].payload
    assert {"id", "sender", "subject", "category", "priority", "summary"} <= set(payload)


def test_fallback_summary() -> None:
    mail = Mail(id="x", sender="a@x.com", subject="Réunion demain", body="...")
    assert _fallback_summary(mail) == "Réunion demain"
    assert _fallback_summary(Mail(id="y", sender="a", subject="", body="")) == "(sans objet)"
