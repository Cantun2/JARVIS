"""Contexte d'exécution injecté aux agents par l'orchestrateur.

Un agent ne reçoit une capacité (inférence, desktop, telegram) que si la permission
correspondante figure dans son contrat. Sinon l'attribut vaut None → accès impossible
par construction, pas par bonne volonté.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Budget, Permission
from jarvis.core.errors import BudgetExceeded, PermissionDenied
from jarvis.core.events import EventType

if TYPE_CHECKING:  # imports uniquement pour le typage — pas de couplage runtime du Core
    from jarvis.desktop.controller import DesktopController
    from jarvis.inference.gateway import InferenceGateway
    from jarvis.io.mail import MailSource
    from jarvis.io.telegram import TelegramNotifier

EmitFn = Callable[[EventType, dict[str, Any]], Awaitable[int]]
TriggerFn = Callable[[str, AgentInput], Awaitable[AgentOutput]]


@dataclass
class BudgetTracker:
    """Suit la consommation d'un run. `0` dans le budget = illimité."""

    budget: Budget
    tokens: int = 0
    usd: float = 0.0

    def charge(self, *, tokens: int = 0, usd: float = 0.0) -> None:
        self.tokens += tokens
        self.usd += usd
        if self.budget.max_tokens_day and self.tokens > self.budget.max_tokens_day:
            raise BudgetExceeded(f"tokens {self.tokens} > {self.budget.max_tokens_day}")
        if self.budget.max_usd_day and self.usd > self.budget.max_usd_day:
            raise BudgetExceeded(f"usd {self.usd:.4f} > {self.budget.max_usd_day}")

    @property
    def spent(self) -> dict[str, float]:
        return {"tokens": float(self.tokens), "usd": round(self.usd, 6)}


@dataclass
class AgentContext:
    """Ce qu'un agent peut utiliser pendant son exécution."""

    agent_name: str
    correlation_id: str
    granted: frozenset[Permission]
    budget: BudgetTracker
    emit_fn: EmitFn
    gateway: InferenceGateway | None = None
    desktop: DesktopController | None = None
    telegram: TelegramNotifier | None = None
    mail: MailSource | None = None
    trigger_fn: TriggerFn | None = None

    async def emit(self, type: EventType, **payload: Any) -> int:
        """Émet un événement au nom de cet agent (source + correlation renseignés)."""
        return await self.emit_fn(type, payload)

    def require_gateway(self) -> InferenceGateway:
        if self.gateway is None:
            raise PermissionDenied(f"{self.agent_name}: NET_CLOUD_INFERENCE non accordée")
        return self.gateway

    def require_desktop(self) -> DesktopController:
        if self.desktop is None:
            raise PermissionDenied(f"{self.agent_name}: permission desktop non accordée")
        return self.desktop

    def require_telegram(self) -> TelegramNotifier:
        if self.telegram is None:
            raise PermissionDenied(f"{self.agent_name}: NOTIFY_TELEGRAM non accordée")
        return self.telegram

    def require_mail(self) -> MailSource:
        if self.mail is None:
            raise PermissionDenied(f"{self.agent_name}: MAIL_READ non accordée")
        return self.mail

    async def trigger(self, name: str, data: AgentInput) -> AgentOutput:
        """Déclenche un autre agent (ex. ATLAS → HERMES) via l'orchestrateur."""
        if self.trigger_fn is None:
            raise PermissionDenied(f"{self.agent_name}: déclenchement d'agents indisponible")
        return await self.trigger_fn(name, data)


@runtime_checkable
class RunnableAgent(Protocol):
    """Contrat structurel d'un agent exécutable par l'orchestrateur."""

    @property
    def contract(self) -> AgentContract: ...

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput: ...
