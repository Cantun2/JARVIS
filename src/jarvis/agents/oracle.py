"""ORACLE — briefing du matin (textuel en Phase 1 ; parlé/TTS plus tard).

Agrège mails urgents + calendrier + Night Report, compose un briefing, l'émet
(`briefing.ready`) et le pousse sur Telegram.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from jarvis.agents.base import JarvisAgent
from jarvis.agents.mocks.night_fixtures import MOCK_NIGHT_REPORT
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Permission
from jarvis.core.events import EventType

DEFAULT_SECTIONS = ("mails_urgents", "calendrier", "night_report", "meteo")

# Agenda factice du jour.
MOCK_CALENDAR = (
    {"time": "10:00", "title": "Point produit"},
    {"time": "14:30", "title": "1:1 avec Marie"},
)
MOCK_WEATHER = "Ciel dégagé, 22°C l'après-midi."


class BriefMail(BaseModel):
    sender: str
    subject: str


class OracleInput(AgentInput):
    urgent_mails: tuple[BriefMail, ...] = ()
    include: tuple[str, ...] = DEFAULT_SECTIONS


class OracleOutput(AgentOutput):
    text: str
    sections: dict[str, Any]


class Oracle(JarvisAgent):
    contract = AgentContract(
        name="ORACLE",
        mode="scheduled",
        permissions=(Permission.NOTIFY_TELEGRAM, Permission.VOICE_IO),
        inputs=OracleInput,
        outputs=OracleOutput,
    )

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, OracleInput)
        # Night Report réel (dry-run) s'il existe, sinon repli sur le mock.
        stored = ctx.tasks.latest_night_report() if ctx.tasks else None
        report = stored or MOCK_NIGHT_REPORT
        sections: dict[str, Any] = {}
        lines: list[str] = ["Bonjour."]

        if "mails_urgents" in data.include:
            n = len(data.urgent_mails)
            sections["mails_urgents"] = [m.model_dump() for m in data.urgent_mails]
            if n:
                lines.append(f"{n} mail(s) urgent(s), dont « {data.urgent_mails[0].subject} ».")
            else:
                lines.append("Aucun mail urgent.")

        if "calendrier" in data.include:
            sections["calendrier"] = list(MOCK_CALENDAR)
            if MOCK_CALENDAR:
                first = MOCK_CALENDAR[0]
                lines.append(f"Premier rendez-vous à {first['time']} : {first['title']}.")

        if "night_report" in data.include:
            sections["night_report"] = report.model_dump()
            lines.append(
                f"VULCAN a terminé {report.done} tâche(s) cette nuit, "
                f"{report.blocked} en attente de ta décision."
            )
            for blocker in report.blockers:
                lines.append(f"À décider : {blocker}")

        if "meteo" in data.include:
            sections["meteo"] = MOCK_WEATHER
            lines.append(f"Météo : {MOCK_WEATHER}")

        text = " ".join(lines)
        await ctx.emit(EventType.BRIEFING_READY, text=text, sections=sections)
        await ctx.require_telegram().notify(text, level="info")
        # Briefing parlé (best-effort) : mock = enregistré ; réel = Piper. Ne bloque rien.
        if ctx.voice is not None:
            await ctx.voice.speak(text)
            await ctx.emit(EventType.VOICE_SPOKE, text=text, intent="briefing", routed_to="ORACLE")
        return OracleOutput(text=text, sections=sections)
