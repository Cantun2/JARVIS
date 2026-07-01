"""Registre des agents : nom → instance + accès aux contrats."""

from __future__ import annotations

from jarvis.core.context import RunnableAgent
from jarvis.core.contracts import AgentContract


class AgentRegistry:
    """Annuaire des agents disponibles, indexé par nom (insensible à la casse)."""

    def __init__(self) -> None:
        self._agents: dict[str, RunnableAgent] = {}

    def register(self, agent: RunnableAgent) -> None:
        key = agent.contract.name.lower()
        if key in self._agents:
            raise ValueError(f"Agent déjà enregistré : {agent.contract.name}")
        self._agents[key] = agent

    def get(self, name: str) -> RunnableAgent:
        try:
            return self._agents[name.lower()]
        except KeyError:
            raise KeyError(f"Agent inconnu : {name}") from None

    def has(self, name: str) -> bool:
        return name.lower() in self._agents

    def all(self) -> list[RunnableAgent]:
        return list(self._agents.values())

    def contracts(self) -> list[AgentContract]:
        return [a.contract for a in self._agents.values()]
