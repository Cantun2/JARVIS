"""La flotte d'agents JARVIS (ATLAS, HERMES, ORACLE, DAEDALUS, ECHO + VULCAN désarmé)."""

from __future__ import annotations

from jarvis.agents.atlas import Atlas
from jarvis.agents.base import JarvisAgent
from jarvis.agents.daedalus import Daedalus
from jarvis.agents.echo import Echo
from jarvis.agents.hermes import Hermes
from jarvis.agents.oracle import Oracle
from jarvis.agents.vulcan import Vulcan


def default_agents() -> list[JarvisAgent]:
    """Instancie la flotte livrée (Phases 1-4)."""
    return [Atlas(), Hermes(), Oracle(), Daedalus(), Echo(), Vulcan()]


__all__ = [
    "Atlas",
    "Daedalus",
    "Echo",
    "Hermes",
    "JarvisAgent",
    "Oracle",
    "Vulcan",
    "default_agents",
]
