"""MockDesktop : backend factice à 3 écrans, enregistre chaque action.

Base des tests desktop et de `make demo` — aucun matériel ni serveur graphique requis.
"""

from __future__ import annotations

from itertools import count

from jarvis.desktop.controller import (
    AppRef,
    DesktopAction,
    DesktopCapabilities,
    DesktopController,
    Geometry,
    Screen,
    WindowPlacementResult,
)

# Configuration cible (portable + 2 externes) simulée pour tester le multi-écran.
_FAKE_SCREENS = [
    Screen("screen-1", "eDP-1 (portable)", Geometry(0, 0, 1920, 1080), primary=True),
    Screen("screen-2", "HDMI-1 (externe G)", Geometry(1920, 0, 2560, 1440)),
    Screen("screen-3", "DP-1 (externe D)", Geometry(4480, 0, 2560, 1440)),
]


class MockDesktop(DesktopController):
    """Enregistre les actions au lieu de les exécuter."""

    def __init__(self, screens: list[Screen] | None = None) -> None:
        self._screens = screens if screens is not None else list(_FAKE_SCREENS)
        self.actions: list[DesktopAction] = []
        self._pids = count(start=1000)

    async def list_screens(self) -> list[Screen]:
        return list(self._screens)

    async def launch_app(self, app_id: str, args: list[str] | None = None) -> AppRef:
        pid = next(self._pids)
        self.actions.append(
            DesktopAction("launch_app", {"app_id": app_id, "args": args or [], "pid": pid})
        )
        return AppRef(app_id=app_id, pid=pid, window_id=f"win-{pid}")

    async def open_url(
        self, url: str, *, profile: str | None = None, browser: str = "default"
    ) -> AppRef:
        pid = next(self._pids)
        self.actions.append(
            DesktopAction(
                "open_url", {"url": url, "profile": profile, "browser": browser, "pid": pid}
            )
        )
        return AppRef(app_id=browser, pid=pid, window_id=f"win-{pid}")

    async def move_window(
        self, app: AppRef, screen_id: str, geometry: Geometry | None = None
    ) -> WindowPlacementResult:
        known = {s.id for s in self._screens}
        placed = screen_id in known
        self.actions.append(
            DesktopAction(
                "move_window",
                {
                    "app_id": app.app_id,
                    "window_id": app.window_id,
                    "screen_id": screen_id,
                    "geometry": geometry.__dict__ if geometry else None,
                    "placed": placed,
                },
            )
        )
        return WindowPlacementResult(
            placed=placed, reason="" if placed else f"écran inconnu: {screen_id}"
        )

    async def focus(self, app: AppRef) -> None:
        self.actions.append(DesktopAction("focus", {"app_id": app.app_id}))

    async def kill_app(self, app: AppRef) -> None:
        self.actions.append(DesktopAction("kill_app", {"app_id": app.app_id, "pid": app.pid}))

    async def capabilities(self) -> DesktopCapabilities:
        return DesktopCapabilities(
            backend="mock", can_launch=True, can_open_url=True, can_place_windows=True
        )

    # Aides pour les tests
    def kinds(self) -> list[str]:
        return [a.kind for a in self.actions]
