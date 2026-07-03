"""ECHO — interface vocale.

Wake-word « Jarvis » → transcription (STT) → routage vers l'orchestrateur → réponse
parlée (TTS). ECHO n'a aucune capacité I/O dangereuse : il ne peut que **déclencher**
d'autres agents via `ctx.trigger` (chemin orchestrateur, contraint par permissions/budget)
et parler via la voix locale. Le routage d'intention est déterministe ; le free-form
retombe sur le gateway en best-effort (repli robuste si CPU lent).
"""

from __future__ import annotations

import asyncio

from jarvis.agents.base import JarvisAgent
from jarvis.agents.hermes import HermesInput, HermesOutput
from jarvis.agents.oracle import OracleInput, OracleOutput
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Budget, Permission
from jarvis.core.events import EventType
from jarvis.inference.types import ChatMessage

# Table d'intention déterministe : premier mot-clé rencontré gagne.
_BRIEFING_KW = ("briefing", "quoi de neuf", "bonjour", "point du jour", "résume ma journée")
_MAIL_KW = ("mail", "mails", "courrier", "inbox", "tri", "trie mes")
_NIGHT_KW = ("nuit", "rapport de nuit", "vulcan", "cette nuit")


class EchoInput(AgentInput):
    utterance: str = ""
    listen: bool = False


class EchoOutput(AgentOutput):
    heard: str
    wake_detected: bool
    intent: str
    routed_to: str | None = None
    response: str
    spoke: bool


class Echo(JarvisAgent):
    contract = AgentContract(
        name="ECHO",
        mode="continuous",
        permissions=(Permission.VOICE_IO, Permission.NET_CLOUD_INFERENCE),
        budget=Budget(max_tokens_day=20_000, max_runtime_min=2),
        inputs=EchoInput,
        outputs=EchoOutput,
    )

    _reply_timeout: float = 12.0

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, EchoInput)
        voice = ctx.require_voice()

        transcript = data.utterance.strip()
        if not transcript and data.listen:
            transcript = await voice.listen()

        wake, command = voice.detect_wake(transcript)
        await ctx.emit(EventType.VOICE_HEARD, transcript=transcript, wake=wake, command=command)
        if not wake:
            # Pas de wake-word : JARVIS reste muet (ne réagit qu'à son nom).
            return EchoOutput(
                heard=transcript,
                wake_detected=False,
                intent="ignored",
                response="",
                spoke=False,
            )

        intent, routed_to, response = await self._handle(command, ctx)
        await voice.speak(response)
        await ctx.emit(EventType.VOICE_SPOKE, text=response, intent=intent, routed_to=routed_to)
        return EchoOutput(
            heard=transcript,
            wake_detected=True,
            intent=intent,
            routed_to=routed_to,
            response=response,
            spoke=True,
        )

    async def _handle(self, command: str, ctx: AgentContext) -> tuple[str, str | None, str]:
        text = command.lower()

        # Le rapport de nuit est testé avant le briefing : « quoi de neuf cette nuit »
        # contient les deux familles de mots-clés, la plus spécifique gagne.
        if any(k in text for k in _NIGHT_KW):
            report = ctx.tasks.latest_night_report() if ctx.tasks else None
            if report is None:
                return "night_report", None, "Aucun rapport de nuit pour l'instant."
            resp = (
                f"Cette nuit, VULCAN a terminé {report.done} tâche(s), "
                f"{report.blocked} en attente de décision."
            )
            return "night_report", None, resp

        if any(k in text for k in _MAIL_KW):
            out = await ctx.trigger("HERMES", HermesInput())
            assert isinstance(out, HermesOutput)
            n_urgent = len(out.urgent)
            total = len(out.triaged)
            resp = f"J'ai trié {total} mail(s), dont {n_urgent} urgent(s)."
            if n_urgent:
                resp += f" Le plus pressant : « {out.urgent[0].subject} »."
            return "mail_triage", "HERMES", resp

        if any(k in text for k in _BRIEFING_KW):
            out = await ctx.trigger("ORACLE", OracleInput())
            assert isinstance(out, OracleOutput)
            return "briefing", "ORACLE", out.text

        return "chat", None, await self._free_form(command, ctx)

    async def _free_form(self, command: str, ctx: AgentContext) -> str:
        """Réponse libre via le modèle, best-effort. Repli déterministe si lent/absent."""
        fallback = "Je n'ai pas d'action pour cette demande, mais je reste à l'écoute."
        if not command:
            return "Oui ? Je vous écoute."
        prompt = f"Réponds en une phrase, en français, à: {command}"
        try:
            resp = await asyncio.wait_for(
                ctx.require_gateway().complete(
                    [ChatMessage(role="user", content=prompt)], tier="local", max_tokens=80
                ),
                timeout=self._reply_timeout,
            )
        except Exception:
            return fallback
        ctx.budget.charge(tokens=resp.usage.total_tokens)
        return resp.text.strip() or fallback
