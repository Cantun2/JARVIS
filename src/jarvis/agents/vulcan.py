"""VULCAN — Night Shift Manager, livré DÉSARMÉ.

Contrat + stub uniquement. `enabled=False` : l'orchestrateur refuse de l'exécuter
(AgentDisarmed) tant que le night shift n'est pas activé manuellement après branchement.
Aucune session nocturne réelle ne peut démarrer en Phase 1.
"""

from __future__ import annotations

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


class VulcanInput(AgentInput):
    task: str = ""
    repo: str = ""


class VulcanOutput(AgentOutput):
    status: str = "disarmed"
    branch: str | None = None
    report: str = ""


class Vulcan(JarvisAgent):
    contract = AgentContract(
        name="VULCAN",
        mode="continuous",
        permissions=(Permission.SHELL_SANDBOXED, Permission.FS_PROJECT_DIRS),
        budget=Budget(max_usd_day=5.0, max_runtime_min=480),
        escalation=EscalationPolicy(
            triggers=(EscalationTrigger.ON_BLOCKED_DECISION, EscalationTrigger.ON_MERGE),
            channel="both",
        ),
        inputs=VulcanInput,
        outputs=VulcanOutput,
        enabled=False,  # DÉSARMÉ — activation manuelle post-branchement.
    )

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        # Défense en profondeur : même appelé directement, VULCAN refuse.
        raise RuntimeError("VULCAN est désarmé (night_shift.enabled=false).")
