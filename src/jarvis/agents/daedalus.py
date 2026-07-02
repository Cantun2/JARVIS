"""DAEDALUS — Project Planner.

Prend un objectif flou → un backlog de tâches exécutables avec critères d'acceptation,
persisté dans le store. Décomposition déterministe (fiable, testable) + enrichissement
best-effort des descriptions via le modèle (repli si lent/absent). Aucune I/O dangereuse.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from jarvis.agents.base import JarvisAgent
from jarvis.core.context import AgentContext
from jarvis.core.contracts import (
    AgentContract,
    AgentInput,
    AgentOutput,
    Budget,
    EscalationPolicy,
    EscalationTrigger,
    Permission,
)
from jarvis.core.events import EventType
from jarvis.inference.gateway import InferenceGateway
from jarvis.inference.types import ChatMessage
from jarvis.night.models import TaskDraft


def _decompose(goal: str) -> list[TaskDraft]:
    """Gabarit de décomposition déterministe d'un objectif en tâches exécutables."""
    g = goal.strip().rstrip(".")
    return [
        TaskDraft(
            title=f"Cadrer et clarifier : {g}",
            acceptance_criteria=(
                "Périmètre écrit",
                "Critères de succès listés",
                "Risques identifiés",
            ),
        ),
        TaskDraft(
            title=f"Concevoir la solution : {g}",
            acceptance_criteria=("Approche technique choisie", "Découpage validé"),
        ),
        TaskDraft(
            title=f"Implémenter : {g}",
            acceptance_criteria=("Code écrit", "Tests unitaires verts", "Lint/type OK"),
        ),
        TaskDraft(
            title=f"Tester et documenter : {g}",
            acceptance_criteria=("Tests d'intégration", "Docs à jour"),
        ),
        TaskDraft(
            title=f"Revue et intégration : {g}",
            acceptance_criteria=("Revue humaine", "Prêt à merger"),
        ),
    ]


class TaskBrief(BaseModel):
    title: str
    acceptance_criteria: tuple[str, ...] = ()


class DaedalusInput(AgentInput):
    goal: str
    project_name: str = "Projet"


class DaedalusOutput(AgentOutput):
    project_id: str
    project_name: str
    tasks: tuple[TaskBrief, ...]


class Daedalus(JarvisAgent):
    contract = AgentContract(
        name="DAEDALUS",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),
        budget=Budget(max_tokens_day=30_000, max_runtime_min=3),
        escalation=EscalationPolicy(
            triggers=(EscalationTrigger.ON_BLOCKED_DECISION,), channel="ui"
        ),
        inputs=DaedalusInput,
        outputs=DaedalusOutput,
    )

    _describe_timeout: float = 12.0

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, DaedalusInput)
        gateway = ctx.require_gateway()
        store = ctx.require_tasks()

        drafts: list[TaskDraft] = []
        for draft in _decompose(data.goal):
            description = await self._describe(gateway, data.goal, draft.title, ctx)
            drafts.append(
                TaskDraft(
                    title=draft.title,
                    description=description,
                    acceptance_criteria=draft.acceptance_criteria,
                )
            )

        project = store.create_project(data.project_name, data.goal)
        tasks = store.add_tasks(project.id, drafts)
        await ctx.emit(
            EventType.BACKLOG_READY,
            project_id=project.id,
            project_name=project.name,
            count=len(tasks),
        )
        return DaedalusOutput(
            project_id=project.id,
            project_name=project.name,
            tasks=tuple(
                TaskBrief(title=t.title, acceptance_criteria=t.acceptance_criteria) for t in tasks
            ),
        )

    async def _describe(
        self, gateway: InferenceGateway, goal: str, title: str, ctx: AgentContext
    ) -> str:
        """Une phrase décrivant la tâche, best-effort. Repli déterministe."""
        prompt = f"Objectif global: {goal}. Décris en une phrase la tâche « {title} »."
        try:
            resp = await asyncio.wait_for(
                gateway.complete(
                    [ChatMessage(role="user", content=prompt)], tier="local", max_tokens=60
                ),
                timeout=self._describe_timeout,
            )
        except Exception:
            return f"Livrer : {title}."
        ctx.budget.charge(tokens=resp.usage.total_tokens)
        return resp.text.strip() or f"Livrer : {title}."
