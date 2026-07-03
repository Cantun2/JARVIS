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
from jarvis.io.mail import MailSource, build_mail
from jarvis.io.telegram import TelegramNotifier, build_telegram
from jarvis.io.voice import VoiceIO, build_voice
from jarvis.mail.store import MailMemory
from jarvis.night.store import TaskStore


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
    mail: MailSource
    voice: VoiceIO
    tasks: TaskStore
    mail_memory: MailMemory

    def close(self) -> None:
        self.journal.close()
        self.tasks.close()
        self.mail_memory.close()


def build_context(settings: Settings | None = None) -> JarvisContext:
    settings = settings or get_settings()
    journal = SQLiteJournal(settings.db_path)
    bus = EventBus(journal=journal)
    enforcer = PermissionEnforcer()
    gateway = build_gateway(settings)
    desktop = build_desktop(settings)
    telegram = build_telegram(settings)
    mail = build_mail(settings)
    voice = build_voice(settings)
    tasks = TaskStore(settings.db_path)
    mail_memory = MailMemory(settings.db_path)
    registry = AgentRegistry()
    runner = AgentRunner(
        bus,
        enforcer,
        registry,
        gateway=gateway,
        desktop=desktop,
        telegram=telegram,
        mail=mail,
        voice=voice,
        tasks=tasks,
        mail_memory=mail_memory,
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
        mail=mail,
        voice=voice,
        tasks=tasks,
        mail_memory=mail_memory,
    )
