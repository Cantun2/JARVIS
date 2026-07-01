"""ProfileExecutor : applique un Day Profile via le Desktop Controller.

Séquence tolérante : kill → launch (global) → par écran (launch/open + placement).
Chaque étape produit une `DesktopAction` et, si fourni, un callback (pour émettre
un événement `desktop.action`). Une app manquante n'interrompt pas la séquence.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from jarvis.desktop.controller import (
    AppRef,
    DesktopAction,
    DesktopController,
    Screen,
)
from jarvis.profiles.models import AppSpec, DayProfile

OnAction = Callable[[DesktopAction], Awaitable[None]]

_BROWSER_KINDS = {"chrome", "chromium", "firefox", "brave", "browser"}
_TAB_ALIASES = {
    "calendar": "https://calendar.google.com",
    "gmail": "https://mail.google.com",
    "meet": "https://meet.google.com",
    "github": "https://github.com",
    "drive": "https://drive.google.com",
}


def _resolve_url(tab: str) -> str:
    if tab in _TAB_ALIASES:
        return _TAB_ALIASES[tab]
    if tab.startswith(("http://", "https://")):
        return tab
    return f"https://{tab}"


@dataclass
class ApplyResult:
    launched: int = 0
    opened: int = 0
    killed: int = 0
    placed: int = 0
    unplaced: int = 0
    actions: list[DesktopAction] = field(default_factory=list)


class ProfileExecutor:
    def __init__(self, desktop: DesktopController, on_action: OnAction | None = None) -> None:
        self._d = desktop
        self._on = on_action
        self._result = ApplyResult()

    async def _emit(self, action: DesktopAction) -> None:
        self._result.actions.append(action)
        if self._on is not None:
            await self._on(action)

    async def apply(self, profile: DayProfile) -> ApplyResult:
        self._result = ApplyResult()
        screens = await self._d.list_screens()

        # 1. Fermer ce qui doit l'être
        for app_id in profile.apps.kill:
            await self._d.kill_app(AppRef(app_id=app_id))
            self._result.killed += 1
            await self._emit(DesktopAction("kill_app", {"app_id": app_id}))

        # 2. Apps globales (sans écran cible)
        for spec in profile.apps.launch:
            await self._spawn(spec, screen=None)

        # 3. Apps par écran (avec placement)
        for idx, specs in profile.layout.screens():
            screen = (
                screens[idx - 1] if idx - 1 < len(screens) else (screens[0] if screens else None)
            )
            for spec in specs:
                await self._spawn(spec, screen=screen)

        return self._result

    async def _spawn(self, spec: AppSpec, *, screen: Screen | None) -> None:
        refs: list[AppRef] = []
        if spec.kind in _BROWSER_KINDS:
            urls = [_resolve_url(t) for t in spec.tabs]
            if not urls and spec.target:
                urls = [_resolve_url(spec.target)]
            for url in urls:
                ref = await self._d.open_url(url, profile=spec.profile, browser=spec.kind)
                refs.append(ref)
                self._result.opened += 1
                await self._emit(DesktopAction("open_url", {"url": url, "profile": spec.profile}))
            if not urls:  # navigateur sans onglet explicite
                ref = await self._d.launch_app(spec.kind)
                refs.append(ref)
                self._result.launched += 1
                await self._emit(DesktopAction("launch_app", {"app_id": spec.kind}))
        else:
            args = [spec.target] if spec.target else []
            ref = await self._d.launch_app(spec.kind, args)
            refs.append(ref)
            self._result.launched += 1
            await self._emit(DesktopAction("launch_app", {"app_id": spec.kind, "args": args}))

        if screen is not None:
            for ref in refs:
                res = await self._d.move_window(ref, screen.id)
                if res.placed:
                    self._result.placed += 1
                else:
                    self._result.unplaced += 1
                await self._emit(
                    DesktopAction(
                        "move_window",
                        {"app_id": ref.app_id, "screen_id": screen.id, "placed": res.placed},
                    )
                )
