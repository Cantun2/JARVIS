"""Sélection du backend Desktop selon la configuration.

Défaut = MockDesktop (aucun matériel/serveur graphique). Le backend GNOME réel n'est
importé que si explicitement demandé (import paresseux → pas de dépendance dure).
"""

from __future__ import annotations

from jarvis.config import Settings
from jarvis.desktop.controller import DesktopController
from jarvis.desktop.mock_desktop import MockDesktop
from jarvis.logging import get_logger

log = get_logger("jarvis.desktop")


def build_desktop(settings: Settings) -> DesktopController:
    if settings.desktop_backend == "gnome" and settings.mode == "real":
        try:
            from jarvis.desktop.gnome_wayland import GnomeWaylandDesktop
        except ImportError as exc:  # backend réel indisponible → repli mock
            log.warning("desktop_backend_fallback", reason=str(exc))
            return MockDesktop()
        log.info("desktop_backend", backend="gnome-wayland")
        return GnomeWaylandDesktop()
    return MockDesktop()
