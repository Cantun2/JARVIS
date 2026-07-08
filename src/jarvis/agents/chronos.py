"""CHRONOS — cerveau de l'agenda : rappelle, signale les RDV, PROPOSE des résolutions.

Nom : Chronos, le temps. Déclenché par le planificateur (tâche de fond) quand des rappels
sont dus. Émet REMINDER_DUE (tâches) / APPOINTMENT_UPCOMING (RDV), marque comme rappelé
(dédup), et **propose** — sans jamais agir seul — en activant l'agent adapté :
mail → HERMES (brouillon), vidéo/viral → PHEME, recherche → web/CHIRON.
"""

from __future__ import annotations

from pydantic import BaseModel

from jarvis.agents.base import JarvisAgent
from jarvis.agents.conversational import ConversationInput, ConversationOutput
from jarvis.agents.hermes import HermesInput, HermesOutput
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Budget, Permission
from jarvis.core.events import EventType
from jarvis.todo.models import Todo, TodoKind

_MAIL_KW = ("mail", "courrier", "répondre", "reply", "relance", "relancer")
_VIDEO_KW = ("vidéo", "video", "viral", "tiktok", "youtube", "reels", "shorts")
_RESEARCH_KW = ("recherche", "research", "cherche", "trouve", "documenter", "sujet")


class Proposal(BaseModel):
    todo_id: str
    agent: str
    text: str


class ChronosInput(AgentInput):
    trigger: str = "scheduled"
    due_ids: tuple[str, ...] = ()
    appointment_ids: tuple[str, ...] = ()


class ChronosOutput(AgentOutput):
    reminders: tuple[str, ...]
    appointments: tuple[str, ...]
    proposals: tuple[Proposal, ...]


class Chronos(JarvisAgent):
    contract = AgentContract(
        name="CHRONOS",
        mode="scheduled",
        permissions=(Permission.NET_WEB, Permission.NOTIFY_TELEGRAM),
        budget=Budget(max_tokens_day=30_000, max_runtime_min=3),
        inputs=ChronosInput,
        outputs=ChronosOutput,
    )

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, ChronosInput)
        todos = ctx.require_todos()

        reminders: list[str] = []
        appointments: list[str] = []
        proposals: list[Proposal] = []

        for todo_id in data.due_ids:
            todo = todos.get(todo_id)
            if todo is None or todo.kind is not TodoKind.TASK:
                continue
            await ctx.emit(
                EventType.REMINDER_DUE, id=todo.id, title=todo.title, date=todo.date, time=todo.time
            )
            todos.mark_reminded(todo.id)
            reminders.append(todo.id)
            proposal = await self._propose(todo, ctx)
            if proposal is not None:
                todos.set_proposal(todo.id, proposal.text)
                await ctx.emit(
                    EventType.AGENT_PROPOSAL, id=todo.id, agent=proposal.agent, text=proposal.text
                )
                proposals.append(proposal)

        for appt_id in data.appointment_ids:
            appt = todos.get(appt_id)
            if appt is None:
                continue
            await ctx.emit(
                EventType.APPOINTMENT_UPCOMING, id=appt.id, title=appt.title, time=appt.time
            )
            todos.mark_reminded(appt.id)
            appointments.append(appt.id)

        await self._digest(ctx, reminders, appointments)
        return ChronosOutput(
            reminders=tuple(reminders),
            appointments=tuple(appointments),
            proposals=tuple(proposals),
        )

    async def _propose(self, todo: Todo, ctx: AgentContext) -> Proposal | None:
        """Propose une résolution en activant l'agent adapté. Best-effort, jamais d'envoi."""
        text = f"{todo.title} {' '.join(todo.tags)}".lower()
        try:
            if any(k in text for k in _MAIL_KW):
                out = await ctx.trigger("HERMES", HermesInput())
                n = len(out.urgent) if isinstance(out, HermesOutput) else 0
                return Proposal(
                    todo_id=todo.id,
                    agent="HERMES",
                    text=f"{n} mail(s) urgent(s) — brouillons de réponse prêts dans l'Inbox.",
                )
            if any(k in text for k in _VIDEO_KW):
                out = await ctx.trigger(
                    "PHEME", ConversationInput(message=f"Idées de vidéos virales : {todo.title}")
                )
                reply = out.reply if isinstance(out, ConversationOutput) else ""
                return Proposal(todo_id=todo.id, agent="PHEME", text=reply[:500])
            if any(k in text for k in _RESEARCH_KW):
                results = await ctx.require_web().search(todo.title, limit=3)
                if results:
                    links = " · ".join(f"{r.title} ({r.url})" for r in results)
                    return Proposal(todo_id=todo.id, agent="WEB", text=f"Pistes : {links}")
        except Exception:
            return None
        return None

    async def _digest(
        self, ctx: AgentContext, reminders: list[str], appointments: list[str]
    ) -> None:
        if not reminders and not appointments:
            return
        if ctx.telegram is None:
            return
        parts = []
        if reminders:
            parts.append(f"{len(reminders)} rappel(s)")
        if appointments:
            parts.append(f"{len(appointments)} rendez-vous")
        await ctx.require_telegram().notify("CHRONOS : " + ", ".join(parts) + " aujourd'hui.")
