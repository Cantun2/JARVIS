"""ATLAS — orchestrateur du réveil (« Good morning, sir »).

Séquence : wake_up → charge le Day Profile → applique le layout desktop →
déclenche HERMES (triage flash) → déclenche ORACLE (briefing).
"""

from __future__ import annotations

from jarvis.agents.base import JarvisAgent
from jarvis.agents.hermes import HermesInput, HermesOutput
from jarvis.agents.oracle import BriefMail, OracleInput
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Permission
from jarvis.core.events import EventType
from jarvis.desktop.controller import DesktopAction
from jarvis.profiles.executor import ProfileExecutor
from jarvis.profiles.loader import load_profile


class AtlasInput(AgentInput):
    profile: str = "deep-work"


class AtlasOutput(AgentOutput):
    profile: str
    launched: int
    opened: int
    placed: int
    unplaced: int
    briefing: str


class Atlas(JarvisAgent):
    contract = AgentContract(
        name="ATLAS",
        mode="scheduled",
        permissions=(Permission.DESKTOP_LAUNCH, Permission.DESKTOP_WINDOW),
        inputs=AtlasInput,
        outputs=AtlasOutput,
    )

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, AtlasInput)
        await ctx.emit(EventType.WAKE_UP, profile=data.profile)

        profile = load_profile(data.profile)
        desktop = ctx.require_desktop()

        async def on_action(action: DesktopAction) -> None:
            await ctx.emit(EventType.DESKTOP_ACTION, kind=action.kind, **action.detail)

        result = await ProfileExecutor(desktop, on_action).apply(profile)
        await ctx.emit(
            EventType.PROFILE_LOADED,
            profile=profile.name,
            launched=result.launched,
            opened=result.opened,
            placed=result.placed,
            unplaced=result.unplaced,
        )

        # Triage flash puis briefing.
        hermes_out = await ctx.trigger("HERMES", HermesInput())
        assert isinstance(hermes_out, HermesOutput)
        urgent = tuple(BriefMail(sender=m.sender, subject=m.subject) for m in hermes_out.urgent)

        oracle_out = await ctx.trigger(
            "ORACLE", OracleInput(urgent_mails=urgent, include=profile.briefing.include)
        )
        briefing = getattr(oracle_out, "text", "")

        return AtlasOutput(
            profile=profile.name,
            launched=result.launched,
            opened=result.opened,
            placed=result.placed,
            unplaced=result.unplaced,
            briefing=briefing,
        )
