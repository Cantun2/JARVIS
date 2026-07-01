"""Interface abstraite du Desktop Controller + types de valeur.

Un seul contrat, plusieurs backends (Mock, GNOME/Wayland). Le placement pixel-précis
peut être indisponible (Wayland sans extension) : `move_window` le signale sans lever.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Geometry:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Screen:
    id: str
    name: str
    geometry: Geometry
    primary: bool = False
    scale: float = 1.0


@dataclass(frozen=True)
class AppRef:
    """Référence à une application/fenêtre lancée."""

    app_id: str
    pid: int | None = None
    window_id: str | None = None


@dataclass(frozen=True)
class WindowPlacementResult:
    placed: bool
    reason: str = ""


@dataclass(frozen=True)
class DesktopCapabilities:
    backend: str
    can_launch: bool
    can_open_url: bool
    can_place_windows: bool


@dataclass(frozen=True)
class DesktopAction:
    """Trace d'une action desktop (pour la démo, les tests et le journal)."""

    kind: str
    detail: dict[str, Any] = field(default_factory=dict)


class DesktopController(ABC):
    """Contrôle des applications, URLs et fenêtres sur un ou plusieurs écrans."""

    @abstractmethod
    async def list_screens(self) -> list[Screen]: ...

    @abstractmethod
    async def launch_app(self, app_id: str, args: list[str] | None = None) -> AppRef: ...

    @abstractmethod
    async def open_url(
        self, url: str, *, profile: str | None = None, browser: str = "default"
    ) -> AppRef: ...

    @abstractmethod
    async def move_window(
        self, app: AppRef, screen_id: str, geometry: Geometry | None = None
    ) -> WindowPlacementResult: ...

    @abstractmethod
    async def focus(self, app: AppRef) -> None: ...

    @abstractmethod
    async def kill_app(self, app: AppRef) -> None: ...

    @abstractmethod
    async def capabilities(self) -> DesktopCapabilities: ...
