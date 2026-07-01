"""Client D-Bus de l'extension GNOME Shell ``jarvis-desktop@jarvis-suit.local``.

Sous Wayland, un client externe ne peut ni énumérer ni déplacer des fenêtres : seul le
compositeur (GNOME Shell) le peut. On délègue donc à une petite extension qui exporte
l'interface ``org.jarvis.DesktopExt`` sur ``/org/jarvis/DesktopExt`` ; ce module en est le
client, via `gdbus call`. Il est testable headless en injectant un `CommandRunner`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from jarvis.desktop.mutter_display import (  # réutilise le mini-parseur GVariant
    _int_of,
    _iter_tuples,
    _parse_string,
    _skip_ws,
    _split_top_level,
)

# (returncode, stdout, stderr)
CommandRunner = Callable[[list[str]], Awaitable[tuple[int, str, str]]]

BUS_NAME = "org.jarvis.DesktopExt"
OBJECT_PATH = "/org/jarvis/DesktopExt"
INTERFACE = "org.jarvis.DesktopExt"


@dataclass(frozen=True)
class WindowInfo:
    """Fenêtre telle que vue par le compositeur."""

    id: str
    wm_class: str
    title: str
    monitor: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class MonitorInfo:
    """Géométrie d'un moniteur, indexé comme dans GNOME Shell."""

    index: int
    x: int
    y: int
    width: int
    height: int


def _call_argv(method: str, *args: str) -> list[str]:
    """Construit l'argv ``gdbus call`` vers l'interface de l'extension."""
    return [
        "gdbus",
        "call",
        "--session",
        "--dest",
        BUS_NAME,
        "--object-path",
        OBJECT_PATH,
        "--method",
        f"{INTERFACE}.{method}",
        *args,
    ]


def _introspect_argv() -> list[str]:
    return [
        "gdbus",
        "introspect",
        "--session",
        "--dest",
        BUS_NAME,
        "--object-path",
        OBJECT_PATH,
    ]


def _unwrap_single_array(text: str) -> str:
    """Extrait le tableau du n-uplet retourné par gdbus, ex. ``([...],)`` -> ``...``."""
    top = text.strip()
    if top.startswith("(") and top.endswith(")"):
        top = top[1:-1].strip()
        if top.endswith(","):
            top = top[:-1].strip()
    if top.startswith("[") and top.endswith("]"):
        top = top[1:-1]
    return top


def _string_field(token: str) -> str:
    tok = token.strip()
    j = _skip_ws(tok, 0)
    if j < len(tok) and tok[j] == "'":
        value, _ = _parse_string(tok, j)
        return value
    return tok


def parse_windows(text: str) -> list[WindowInfo]:
    """Parse la valeur de ``ListWindows`` : ``a(sssiiiii)``."""
    inner = _unwrap_single_array(text)
    windows: list[WindowInfo] = []
    for body in _iter_tuples(inner):
        f = _split_top_level(body)
        if len(f) < 8:
            continue
        windows.append(
            WindowInfo(
                id=_string_field(f[0]),
                wm_class=_string_field(f[1]),
                title=_string_field(f[2]),
                monitor=_int_of(f[3]),
                x=_int_of(f[4]),
                y=_int_of(f[5]),
                width=_int_of(f[6]),
                height=_int_of(f[7]),
            )
        )
    return windows


def parse_monitors(text: str) -> list[MonitorInfo]:
    """Parse la valeur de ``ListMonitors`` : ``a(iiiii)``."""
    inner = _unwrap_single_array(text)
    monitors: list[MonitorInfo] = []
    for body in _iter_tuples(inner):
        f = _split_top_level(body)
        if len(f) < 5:
            continue
        monitors.append(
            MonitorInfo(
                index=_int_of(f[0]),
                x=_int_of(f[1]),
                y=_int_of(f[2]),
                width=_int_of(f[3]),
                height=_int_of(f[4]),
            )
        )
    return monitors


def parse_string_return(text: str) -> str:
    """Extrait la 1re chaîne d'un retour ``('...',)`` (ex. ``GetWindowByPid``)."""
    top = text.strip()
    if top.startswith("(") and top.endswith(")"):
        top = top[1:-1].strip()
    return _string_field(top)


def parse_bool_return(text: str) -> bool:
    """Extrait le booléen d'un retour ``(true,)`` / ``(false,)``."""
    top = text.strip().lower()
    return "true" in top


class GnomeExtensionClient:
    """Client haut niveau de l'extension. Toutes les méthodes sont async et injectables."""

    def __init__(self, runner: CommandRunner) -> None:
        self._run = runner

    async def available(self) -> bool:
        """`True` si le bus name de l'extension répond à l'introspection."""
        try:
            code, _out, _err = await self._run(_introspect_argv())
        except OSError:
            return False
        return code == 0

    async def list_windows(self) -> list[WindowInfo]:
        code, out, _err = await self._run(_call_argv("ListWindows"))
        if code != 0:
            return []
        return parse_windows(out)

    async def list_monitors(self) -> list[MonitorInfo]:
        code, out, _err = await self._run(_call_argv("ListMonitors"))
        if code != 0:
            return []
        return parse_monitors(out)

    async def move_window(
        self, window_id: str, monitor: int, x: int, y: int, width: int, height: int
    ) -> bool:
        argv = _call_argv(
            "MoveWindow",
            window_id,
            str(monitor),
            str(x),
            str(y),
            str(width),
            str(height),
        )
        code, out, _err = await self._run(argv)
        return code == 0 and parse_bool_return(out)

    async def focus_window(self, window_id: str) -> bool:
        code, out, _err = await self._run(_call_argv("FocusWindow", window_id))
        return code == 0 and parse_bool_return(out)

    async def close_window(self, window_id: str) -> bool:
        code, out, _err = await self._run(_call_argv("CloseWindow", window_id))
        return code == 0 and parse_bool_return(out)

    async def get_window_by_pid(self, pid: int) -> str:
        code, out, _err = await self._run(_call_argv("GetWindowByPid", str(pid)))
        if code != 0:
            return ""
        return parse_string_return(out)


# Le mini-parseur GVariant est importé pour être réutilisé ; ces symboles gardent l'API
# de ce module cohérente (ré-export explicite).
__all__ = [
    "BUS_NAME",
    "INTERFACE",
    "OBJECT_PATH",
    "CommandRunner",
    "GnomeExtensionClient",
    "MonitorInfo",
    "WindowInfo",
    "parse_bool_return",
    "parse_monitors",
    "parse_string_return",
    "parse_windows",
]
