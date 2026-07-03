"""AgentRunner — le seul chemin d'exécution d'un agent.

Séquence : contrat activé ? → permissions → budget → contexte de capacités →
run (avec timeout) → événements de cycle de vie + enregistrement du run.
Rien ne contourne ce chemin.
"""

from __future__ import annotations

import asyncio
from typing import Any

from jarvis.core.bus import EventBus
from jarvis.core.context import AgentContext, BudgetTracker, RunnableAgent
from jarvis.core.contracts import AgentInput, AgentOutput, Permission
from jarvis.core.errors import (
    AgentDisarmed,
    BudgetExceeded,
    EscalationRequired,
    PermissionDenied,
)
from jarvis.core.events import Event, EventType, uuid7
from jarvis.core.permissions import PermissionEnforcer
from jarvis.core.registry import AgentRegistry
from jarvis.logging import get_logger

log = get_logger("jarvis.orchestrator")

_DESKTOP_PERMS = {Permission.DESKTOP_LAUNCH, Permission.DESKTOP_WINDOW}


class AgentRunner:
    """Exécute les agents en appliquant contrat, permissions et budget."""

    def __init__(
        self,
        bus: EventBus,
        enforcer: PermissionEnforcer,
        registry: AgentRegistry,
        *,
        gateway: Any | None = None,
        desktop: Any | None = None,
        telegram: Any | None = None,
        mail: Any | None = None,
        voice: Any | None = None,
        tasks: Any | None = None,
        mail_memory: Any | None = None,
    ) -> None:
        self.bus = bus
        self.enforcer = enforcer
        self.registry = registry
        self.gateway = gateway
        self.desktop = desktop
        self.telegram = telegram
        self.mail = mail
        self.voice = voice
        self.tasks = tasks
        self.mail_memory = mail_memory

    async def run_by_name(self, name: str, data: AgentInput) -> AgentOutput:
        return await self.run(self.registry.get(name), data)

    async def run(self, agent: RunnableAgent, data: AgentInput) -> AgentOutput:
        contract = agent.contract
        corr = uuid7()
        journal = self.bus.journal

        async def emit(etype: EventType, payload: dict[str, Any]) -> int:
            return await self.bus.publish(
                Event(type=etype, source=contract.name, correlation_id=corr, payload=payload)
            )

        # 1. Agent désarmé ?
        if not contract.enabled:
            await emit(EventType.AGENT_FAILED, {"error": "disarmed", "agent": contract.name})
            raise AgentDisarmed(f"Agent '{contract.name}' est désarmé (enabled=False)")

        # 2. Permissions
        try:
            self.enforcer.check(contract)
        except PermissionDenied as exc:
            await emit(EventType.PERMISSION_DENIED, {"error": str(exc)})
            raise

        # 3. Validation de l'entrée
        if not isinstance(data, contract.inputs):
            raise TypeError(
                f"{contract.name}: entrée {type(data).__name__}, attendu {contract.inputs.__name__}"
            )

        # 4. Budget + contexte de capacités (gaté par permission)
        granted = self.enforcer.granted(contract)
        budget = BudgetTracker(contract.budget)
        ctx = AgentContext(
            agent_name=contract.name,
            correlation_id=corr,
            granted=granted,
            budget=budget,
            emit_fn=emit,
            gateway=self.gateway if Permission.NET_CLOUD_INFERENCE in granted else None,
            desktop=self.desktop if granted & _DESKTOP_PERMS else None,
            telegram=self.telegram if Permission.NOTIFY_TELEGRAM in granted else None,
            mail=self.mail if Permission.MAIL_READ in granted else None,
            voice=self.voice if Permission.VOICE_IO in granted else None,
            tasks=self.tasks,
            mail_memory=self.mail_memory,
            trigger_fn=self.run_by_name,
        )

        # 5. Exécution
        journal.record_run_start(corr, contract.name)
        await emit(EventType.AGENT_STARTED, {"input": data.model_dump(mode="json")})
        timeout = contract.budget.max_runtime_min * 60 or None
        try:
            out = await asyncio.wait_for(agent.run(data, ctx), timeout=timeout)
        except EscalationRequired as exc:
            await emit(
                EventType.AGENT_ESCALATED,
                {"question": exc.question, "options": exc.options, "context": exc.context},
            )
            journal.record_run_end(
                corr, "escalated", tokens=budget.tokens, usd=budget.usd, error=exc.question
            )
            raise
        except BudgetExceeded as exc:
            await emit(EventType.BUDGET_EXCEEDED, {"error": str(exc)})
            journal.record_run_end(
                corr, "failed", tokens=budget.tokens, usd=budget.usd, error=str(exc)
            )
            raise
        except TimeoutError:
            await emit(EventType.AGENT_FAILED, {"error": "timeout"})
            journal.record_run_end(
                corr, "failed", tokens=budget.tokens, usd=budget.usd, error="timeout"
            )
            raise
        except Exception as exc:
            await emit(EventType.AGENT_FAILED, {"error": str(exc), "kind": type(exc).__name__})
            journal.record_run_end(
                corr, "failed", tokens=budget.tokens, usd=budget.usd, error=str(exc)
            )
            log.exception("agent_failed", agent=contract.name)
            raise

        # 6. Succès
        await emit(
            EventType.AGENT_FINISHED, {"output": out.model_dump(mode="json"), "cost": budget.spent}
        )
        journal.record_run_end(corr, "finished", tokens=budget.tokens, usd=budget.usd)
        return out
