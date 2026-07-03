"""ECHO : wake-word, routage d'intention, déclenchement d'agents, voix."""

from __future__ import annotations

from jarvis.agents.echo import Echo, EchoInput, EchoOutput
from jarvis.assembly import JarvisContext
from jarvis.core.events import EventType
from jarvis.io.voice import MockTTS


async def test_echo_ignores_without_wake_word(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Echo(), EchoInput(utterance="fais le briefing"))
    assert isinstance(out, EchoOutput)
    assert out.wake_detected is False
    assert out.spoke is False and out.response == ""
    # A entendu mais n'a pas parlé.
    assert ctx.journal.replay(types=[EventType.VOICE_HEARD])
    assert not ctx.journal.replay(types=[EventType.VOICE_SPOKE])


async def test_echo_routes_briefing_to_oracle(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Echo(), EchoInput(utterance="Jarvis, fais-moi le briefing"))
    assert isinstance(out, EchoOutput)
    assert out.wake_detected is True
    assert out.intent == "briefing" and out.routed_to == "ORACLE"
    assert out.response.startswith("Bonjour.")
    assert out.spoke is True
    # ORACLE a bien tourné (briefing émis) et ECHO a parlé.
    assert ctx.journal.replay(types=[EventType.BRIEFING_READY])
    assert ctx.journal.replay(types=[EventType.VOICE_SPOKE])


async def test_echo_routes_mail_to_hermes(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Echo(), EchoInput(utterance="Jarvis, trie mes mails"))
    assert isinstance(out, EchoOutput)
    assert out.intent == "mail_triage" and out.routed_to == "HERMES"
    assert "trié" in out.response
    assert ctx.journal.replay(types=[EventType.MAIL_TRIAGED])


async def test_echo_night_report_without_report(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Echo(), EchoInput(utterance="Jarvis, quoi de neuf cette nuit ?"))
    assert isinstance(out, EchoOutput)
    assert out.intent == "night_report" and out.routed_to is None
    assert "Aucun rapport" in out.response


async def test_echo_speaks_through_voice(ctx: JarvisContext) -> None:
    await ctx.runner.run(Echo(), EchoInput(utterance="Jarvis, le briefing"))
    assert isinstance(ctx.voice.tts, MockTTS)
    # ORACLE (briefing parlé) + ECHO (réponse) → au moins un clip.
    assert ctx.voice.tts.clips
    assert any(c.text.startswith("Bonjour.") for c in ctx.voice.tts.clips)


async def test_echo_free_form_falls_back(ctx: JarvisContext) -> None:
    out = await ctx.runner.run(Echo(), EchoInput(utterance="Jarvis, raconte une blague"))
    assert isinstance(out, EchoOutput)
    assert out.intent == "chat" and out.routed_to is None
    assert out.response  # une réponse (modèle mock ou repli déterministe)
    assert out.spoke is True
