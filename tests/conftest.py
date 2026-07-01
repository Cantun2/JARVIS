"""Fixtures partagées."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.assembly import JarvisContext, build_context
from jarvis.config import Settings
from jarvis.core.bus import EventBus
from jarvis.core.journal import SQLiteJournal
from jarvis.core.orchestrator import AgentRunner
from jarvis.core.permissions import PermissionEnforcer
from jarvis.core.registry import AgentRegistry


@pytest.fixture
def journal() -> Iterator[SQLiteJournal]:
    j = SQLiteJournal(":memory:")
    yield j
    j.close()


@pytest.fixture
def bus(journal: SQLiteJournal) -> EventBus:
    return EventBus(journal=journal)


@pytest.fixture
def enforcer() -> PermissionEnforcer:
    return PermissionEnforcer()


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry()


@pytest.fixture
def runner(bus: EventBus, enforcer: PermissionEnforcer, registry: AgentRegistry) -> AgentRunner:
    return AgentRunner(bus, enforcer, registry)


@pytest.fixture
def ctx() -> Iterator[JarvisContext]:
    """Contexte complet câblé en mode mock, journal en mémoire."""
    context = build_context(Settings(mode="mock", db_path=":memory:"))
    yield context
    context.close()
