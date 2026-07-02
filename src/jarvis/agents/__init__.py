"""La flotte d'agents JARVIS (Phase 1 : ATLAS, HERMES, ORACLE + VULCAN désarmé)."""

from __future__ import annotations

from jarvis.agents.atlas import Atlas
from jarvis.agents.base import JarvisAgent
from jarvis.agents.daedalus import Daedalus
from jarvis.agents.hermes import Hermes
from jarvis.agents.oracle import Oracle
from jarvis.agents.vulcan import Vulcan


def default_agents() -> list[JarvisAgent]:
    """Instancie la flotte livrée (Phases 1-3)."""
    return [Atlas(), Hermes(), Oracle(), Daedalus(), Vulcan()]


__all__ = ["Atlas", "Daedalus", "Hermes", "JarvisAgent", "Oracle", "Vulcan", "default_agents"]
