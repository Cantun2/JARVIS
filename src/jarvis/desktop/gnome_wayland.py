"""Backend Desktop RÉEL pour GNOME 46 sous Wayland.

Assemble trois briques :
  * lancement d'applications et ouverture d'URL via les outils standards du poste
    (`gtk-launch`, `gio launch`, `xdg-open`, ou une ligne dédiée par navigateur+profil) ;
  * découverte des écrans via Mutter (`mutter_display`) ;
  * placement / focus / fermeture de fenêtres via l'extension GNOME Shell
    (`gnome_extension`), seule voie fiable sous Wayland.

Tout passe par un `CommandRunner` injectable : par défaut un runner réel basé sur
`asyncio.create_subprocess_exec`, remplaçable par un faux runner dans les tests (aucun
test ne dépend d'un vrai GNOME).
"""

from __future__ import annotations

import asyncio
import re
import shlex

from jarvis.desktop.controller import (
    AppRef,
    DesktopCapabilities,
    DesktopController,
    Geometry,
    Screen,
    WindowPlacementResult,
)
from jarvis.desktop.gnome_extension import CommandRunner, GnomeExtensionClient
from jarvis.desktop.mutter_display import DISPLAY_STATE_ARGV, parse_display_state

_PID_RE = re.compile(r"pid[\s:=]+(\d+)", re.IGNORECASE)


async def _real_runner(argv: list[str]) -> tuple[int, str, str]:
    """Exécute réellement une commande et renvoie ``(returncode, stdout, stderr)``."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out_b, err_b = await proc.communicate()
    code = proc.returncode if proc.returncode is not None else -1
    return code, out_b.decode("utf-8", "replace"), err_b.decode("utf-8", "replace")


def _app_desktop_id(app_id: str) -> str:
    """Normalise un identifiant d'appli en fichier ``.desktop`` pour `gtk-launch`."""
    return app_id if app_id.endswith(".desktop") else f"{app_id}.desktop"


def build_launch_argv(app_id: str, args: list[str] | None) -> list[str]:
    """Construit l'argv de lancement via ``gtk-launch <app>.desktop [args...]``."""
    argv = ["gtk-launch", _app_desktop_id(app_id)]
    if args:
        argv.extend(args)
    return argv


def build_gio_launch_argv(app_id: str, args: list[str] | None) -> list[str]:
    """Construit l'argv de secours via ``gio launch <app>.desktop [args...]``."""
    argv = ["gio", "launch", _app_desktop_id(app_id)]
    if args:
        argv.extend(args)
    return argv


def build_open_url_argv(url: str, *, profile: str | None, browser: str) -> list[str]:
    """Construit l'argv d'ouverture d'URL.

    Sans profil : ``xdg-open <url>`` (respecte le navigateur par défaut du poste).
    Avec profil : une ligne dédiée selon ``browser`` (``chrome``/``google-chrome`` ou
    ``firefox``/``firefox-esr``…) car ``xdg-open`` ne sait pas cibler un profil.
    """
    if not profile:
        return ["xdg-open", url]

    key = browser.lower()
    if key in {"firefox", "firefox-esr", "mozilla"}:
        return ["firefox", "-P", profile, url]
    if key in {"chrome", "google-chrome", "google-chrome-stable", "chromium", "default"}:
        exe = "chromium" if key == "chromium" else "google-chrome"
        return [exe, f"--profile-directory={profile}", url]
    # Navigateur inconnu mais profil demandé : on tente la convention Chrome.
    return [browser, f"--profile-directory={profile}", url]


def _extract_pid(stdout: str, stderr: str) -> int | None:
    """Tente de récupérer un PID depuis la sortie de ``gio launch`` (best effort)."""
    for stream in (stdout, stderr):
        m = _PID_RE.search(stream)
        if m:
            return int(m.group(1))
    return None


class GnomeWaylandDesktop(DesktopController):
    """Contrôleur desktop réel GNOME 46 / Wayland (dégradation propre sans extension)."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._run: CommandRunner = runner if runner is not None else _real_runner
        self._ext = GnomeExtensionClient(self._run)

    # ----------------------------------------------------------------- écrans
    async def list_screens(self) -> list[Screen]:
        code, out, _err = await self._run(list(DISPLAY_STATE_ARGV))
        if code != 0:
            return []
        return parse_display_state(out)

    # ------------------------------------------------------------- lancement
    async def launch_app(self, app_id: str, args: list[str] | None = None) -> AppRef:
        argv = build_launch_argv(app_id, args)
        code, out, err = await self._run(argv)
        if code != 0:
            # Repli sur `gio launch`, qui peut aussi révéler un PID.
            argv = build_gio_launch_argv(app_id, args)
            code, out, err = await self._run(argv)
        pid = _extract_pid(out, err) if code == 0 else None
        return AppRef(app_id=app_id, pid=pid)

    async def open_url(
        self, url: str, *, profile: str | None = None, browser: str = "default"
    ) -> AppRef:
        argv = build_open_url_argv(url, profile=profile, browser=browser)
        await self._run(argv)
        app_id = "xdg-open" if not profile else argv[0]
        return AppRef(app_id=app_id)

    # ------------------------------------------------------------- fenêtres
    async def _monitor_index_for(self, screen_id: str) -> int | None:
        """Mappe un ``screen_id`` (connecteur) vers l'index moniteur de GNOME Shell.

        On aligne l'ordre des moniteurs de l'extension (`ListMonitors`, indexés) sur les
        `Screen` de Mutter en comparant leur position (x, y), robuste au changement d'ordre.
        """
        screens = await self.list_screens()
        target: Screen | None = next((s for s in screens if s.id == screen_id), None)
        if target is None:
            return None

        monitors = await self._ext.list_monitors()
        for mon in monitors:
            if mon.x == target.geometry.x and mon.y == target.geometry.y:
                return mon.index
        # Repli : position du screen dans l'ordre Mutter.
        try:
            return [s.id for s in screens].index(screen_id)
        except ValueError:
            return None

    async def _resolve_window_id(self, app: AppRef) -> str | None:
        """Détermine l'ID de fenêtre exploitable par l'extension."""
        if app.window_id:
            return app.window_id
        if app.pid is not None:
            wid = await self._ext.get_window_by_pid(app.pid)
            if wid:
                return wid
        return None

    async def move_window(
        self, app: AppRef, screen_id: str, geometry: Geometry | None = None
    ) -> WindowPlacementResult:
        if not await self._ext.available():
            return WindowPlacementResult(placed=False, reason="extension_unavailable")

        monitor = await self._monitor_index_for(screen_id)
        if monitor is None:
            return WindowPlacementResult(placed=False, reason=f"unknown_screen:{screen_id}")

        window_id = await self._resolve_window_id(app)
        if window_id is None:
            return WindowPlacementResult(placed=False, reason="window_not_found")

        if geometry is None:
            screens = await self.list_screens()
            target = next((s for s in screens if s.id == screen_id), None)
            geometry = target.geometry if target else Geometry(0, 0, 0, 0)

        ok = await self._ext.move_window(
            window_id,
            monitor,
            geometry.x,
            geometry.y,
            geometry.width,
            geometry.height,
        )
        if not ok:
            return WindowPlacementResult(placed=False, reason="move_failed")
        return WindowPlacementResult(placed=True)

    async def focus(self, app: AppRef) -> None:
        if not await self._ext.available():
            return
        window_id = await self._resolve_window_id(app)
        if window_id is not None:
            await self._ext.focus_window(window_id)

    async def kill_app(self, app: AppRef) -> None:
        # Voie 1 : fermeture propre via l'extension si une fenêtre est identifiable.
        if await self._ext.available():
            window_id = await self._resolve_window_id(app)
            if window_id is not None:
                await self._ext.close_window(window_id)
                return
        # Voie 2 : repli signal POSIX si on connaît le PID.
        if app.pid is not None:
            await self._run(["kill", str(app.pid)])

    # --------------------------------------------------------- capacités
    async def capabilities(self) -> DesktopCapabilities:
        can_place = await self._ext.available()
        return DesktopCapabilities(
            backend="gnome-wayland",
            can_launch=True,
            can_open_url=True,
            can_place_windows=can_place,
        )


def render_command(argv: list[str]) -> str:
    """Rend un argv en ligne shell lisible (journal/démo)."""
    return " ".join(shlex.quote(part) for part in argv)
