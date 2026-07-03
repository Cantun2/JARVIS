"""Contrats d'agent : permissions, budget, escalade, entrées/sorties typées.

Un agent sans contrat ne tourne pas. Le contrat est un descripteur immuable
consommé par l'orchestrateur (`AgentRunner`), seul point d'exécution.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentMode = Literal["on_demand", "scheduled", "continuous"]


class Permission(StrEnum):
    """Capacités qu'un agent peut demander. Accordées explicitement, jamais implicites."""

    MAIL_READ = "mail.read"
    MAIL_DRAFT = "mail.draft"
    MAIL_SEND = "mail.send"  # jamais accordée par défaut (cf. PermissionEnforcer)
    DESKTOP_LAUNCH = "desktop.launch"
    DESKTOP_WINDOW = "desktop.window"
    FS_PROJECT_DIRS = "fs.project_dirs"
    SHELL_SANDBOXED = "shell.sandboxed"
    NET_CLOUD_INFERENCE = "net.cloud_inference"
    NOTIFY_TELEGRAM = "notify.telegram"
    VOICE_IO = "voice.io"


class Budget(BaseModel):
    """Plafonds par exécution/jour. `0` = illimité (utile en mock)."""

    model_config = ConfigDict(frozen=True)

    max_tokens_day: int = 0
    max_usd_day: float = 0.0
    max_runtime_min: float = 5.0


class EscalationTrigger(StrEnum):
    ON_MAIL_SEND = "on_mail_send"
    ON_MERGE = "on_merge"
    ON_BLOCKED_DECISION = "on_blocked_decision"
    ON_BUDGET_80 = "on_budget_80"


class EscalationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    triggers: tuple[EscalationTrigger, ...] = ()
    channel: Literal["ui", "telegram", "both"] = "ui"


class AgentInput(BaseModel):
    """Base des entrées d'agent. `extra="forbid"` : aucune donnée non déclarée."""

    model_config = ConfigDict(extra="forbid")


class AgentOutput(BaseModel):
    """Base des sorties d'agent."""

    model_config = ConfigDict(extra="forbid")


class AgentContract(BaseModel):
    """Descripteur d'un agent. Immuable."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    mode: AgentMode
    permissions: tuple[Permission, ...] = ()
    budget: Budget = Field(default_factory=Budget)
    escalation: EscalationPolicy = Field(default_factory=EscalationPolicy)
    inputs: type[AgentInput]
    outputs: type[AgentOutput]
    enabled: bool = True  # VULCAN est livré enabled=False (désarmé)

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions
