"""La flotte d'agents JARVIS (ATLAS, HERMES, ORACLE, DAEDALUS, ECHO + VULCAN désarmé)."""

from __future__ import annotations

from jarvis.agents.arachne import Arachne
from jarvis.agents.atlas import Atlas
from jarvis.agents.base import JarvisAgent
from jarvis.agents.chiron import Chiron
from jarvis.agents.chronos import Chronos
from jarvis.agents.daedalus import Daedalus
from jarvis.agents.echo import Echo
from jarvis.agents.hermes import Hermes
from jarvis.agents.jarvis import Jarvis
from jarvis.agents.nemesis import Nemesis
from jarvis.agents.oracle import Oracle
from jarvis.agents.pheme import Pheme
from jarvis.agents.vulcan import Vulcan


def default_agents() -> list[JarvisAgent]:
    """Instancie la flotte livrée (agents de tâche + assistant + experts conversationnels)."""
    return [
        Atlas(),
        Hermes(),
        Oracle(),
        Daedalus(),
        Echo(),
        Jarvis(),
        Pheme(),
        Arachne(),
        Chiron(),
        Nemesis(),
        Chronos(),
        Vulcan(),
    ]


__all__ = [
    "Arachne",
    "Atlas",
    "Chiron",
    "Chronos",
    "Daedalus",
    "Echo",
    "Hermes",
    "Jarvis",
    "JarvisAgent",
    "Nemesis",
    "Oracle",
    "Pheme",
    "Vulcan",
    "default_agents",
]
