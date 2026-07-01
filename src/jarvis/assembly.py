"""Composition root : assemble tous les composants du Core en un contexte partagé.

Utilisé par l'API (`api/app.py`), la démo, le doctor et les tests. Un seul endroit
qui câble bus, journal, permissions, inférence, desktop, telegram, agents et runner.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.agents import default_agents
from jarvis.config import Settings, get_settings
from jarvis.core.bus import EventBus
from jarvis.core.journal import SQLiteJournal
from jarvis.core.orchestrator import AgentRunner
from jarvis.core.permissions import PermissionEnforcer
from jarvis.core.registry import AgentRegistry
from jarvis.desktop.controller import DesktopController
from jarvis.desktop.factory import build_desktop
from jarvis.inference.factory import build_gateway
from jarvis.inference.gateway import InferenceGateway
from jarvis.io.telegram import TelegramNotifier, build_telegram


@dataclass
class JarvisContext:
    settings: Settings
    journal: SQLiteJournal
    bus: EventBus
    enforcer: PermissionEnforcer
    registry: AgentRegistry
    runner: AgentRunner
    gateway: InferenceGateway
    desktop: DesktopController
    telegram: TelegramNotifier

    def close(self) -> None:
        self.journal.close()


def build_context(settings: Settings | None = None) -> JarvisContext:
    settings = settings or get_settings()
    journal = SQLiteJournal(settings.db_path)
    bus = EventBus(journal=journal)
    enforcer = PermissionEnforcer()
    gateway = build_gateway(settings)
    desktop = build_desktop(settings)
    telegram = build_telegram(settings)
    registry = AgentRegistry()
    runner = AgentRunner(
        bus, enforcer, registry, gateway=gateway, desktop=desktop, telegram=telegram
    )
    for agent in default_agents():
        registry.register(agent)
    return JarvisContext(
        settings=settings,
        journal=journal,
        bus=bus,
        enforcer=enforcer,
        registry=registry,
        runner=runner,
        gateway=gateway,
        desktop=desktop,
        telegram=telegram,
    )
