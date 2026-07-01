"""Base commune des agents JARVIS."""

from __future__ import annotations

from abc import ABC, abstractmethod

from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput


class JarvisAgent(ABC):
    """Tout agent expose un `contract` (descripteur) et une coroutine `run`.

    L'agent ne touche jamais une ressource directement : il passe par `ctx`,
    qui ne contient que les capacités accordées par le contrat.
    """

    contract: AgentContract

    @abstractmethod
    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput: ...
