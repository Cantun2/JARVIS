"""Tests headless du backend GNOME/Wayland : parsing d'écrans, argv, dégradation, capacités.

Aucun test ne dépend d'un vrai GNOME : on injecte un faux `CommandRunner` qui capture les
commandes et renvoie des sorties canned (dont un échantillon réaliste de
`DisplayConfig.GetCurrentState`, au format GVariant texte de `gdbus`).
"""

from __future__ import annotations

from jarvis.desktop.controller import AppRef, Geometry
from jarvis.desktop.gnome_extension import (
    parse_monitors,
    parse_string_return,
    parse_windows,
)
from jarvis.desktop.gnome_wayland import (
    GnomeWaylandDesktop,
    build_launch_argv,
    build_open_url_argv,
)
from jarvis.desktop.mutter_display import parse_display_state

# --------------------------------------------------------------------------------------
# Échantillon RÉALISTE capturé de `gdbus call ... GetCurrentState`, étendu à 3 moniteurs :
#   * eDP-1  (portable) : 1920x1080, scale 1.0, primary, à (0,0)
#   * HDMI-1 (externe)  : 2560x1440, scale 1.0,          à (1920,0)
#   * DP-1   (externe)  : 3840x2160, scale 2.0,          à (4480,0)  -> 1920x1080 logique
# Structure : (serial, a[monitors physiques], a[monitors LOGIQUES], {props globales}).
# --------------------------------------------------------------------------------------
DISPLAY_STATE_SAMPLE = (
    "(uint32 42, "
    "[(('eDP-1', 'AUO', '0x463d', '0x00000000'), "
    "[('1920x1080@60.049', 1920, 1080, 60.049, 1.0, [1.0, 2.0], "
    "{'is-current': <true>, 'is-preferred': <true>}), "
    "('1600x900@59.946', 1600, 900, 59.946, 1.0, [1.0], {})], "
    "{'is-builtin': <true>, 'display-name': <'Affichage intégré'>}), "
    "(('HDMI-1', 'DEL', '0x1234', '0x0005A3B2'), "
    "[('2560x1440@59.951', 2560, 1440, 59.951, 1.0, [1.0, 2.0], "
    "{'is-current': <true>, 'is-preferred': <true>}), "
    "('1920x1080@60.000', 1920, 1080, 60.0, 1.0, [1.0], {})], "
    "{'display-name': <'DELL U2719D'>}), "
    "(('DP-1', 'DEL', '0x9abc', '0x000112FF'), "
    "[('3840x2160@59.997', 3840, 2160, 59.997, 1.0, [1.0, 2.0], "
    "{'is-current': <true>, 'is-preferred': <true>})], "
    "{'display-name': <'DELL U2720Q'>})], "
    "[(0, 0, 1.0, uint32 0, true, "
    "[('eDP-1', 'AUO', '0x463d', '0x00000000')], @a{sv} {}), "
    "(1920, 0, 1.0, uint32 0, false, "
    "[('HDMI-1', 'DEL', '0x1234', '0x0005A3B2')], @a{sv} {}), "
    "(4480, 0, 2.0, uint32 0, false, "
    "[('DP-1', 'DEL', '0x9abc', '0x000112FF')], @a{sv} {})], "
    "{'renderer': <'native'>, 'layout-mode': <uint32 2>})"
)


# ============================================================ parse_display_state (pur)
def test_parse_display_state_three_logical_monitors() -> None:
    screens = parse_display_state(DISPLAY_STATE_SAMPLE)
    assert [s.id for s in screens] == ["eDP-1", "HDMI-1", "DP-1"]


def test_parse_display_state_positions_and_sizes() -> None:
    screens = parse_display_state(DISPLAY_STATE_SAMPLE)
    edp, hdmi, dp = screens

    assert edp.geometry == Geometry(0, 0, 1920, 1080)
    assert edp.primary is True
    assert edp.scale == 1.0

    assert hdmi.geometry == Geometry(1920, 0, 2560, 1440)
    assert hdmi.primary is False

    # scale 2.0 => taille logique = 3840x2160 / 2 = 1920x1080.
    assert dp.scale == 2.0
    assert dp.geometry == Geometry(4480, 0, 1920, 1080)


def test_parse_display_state_empty_is_safe() -> None:
    assert parse_display_state("") == []
    assert parse_display_state("(uint32 1,)") == []


# ============================================================ construction des argv
def test_build_launch_argv_adds_desktop_suffix() -> None:
    assert build_launch_argv("code", None) == ["gtk-launch", "code.desktop"]


def test_build_launch_argv_keeps_existing_suffix_and_args() -> None:
    argv = build_launch_argv("org.gnome.Nautilus.desktop", ["~/projets"])
    assert argv == ["gtk-launch", "org.gnome.Nautilus.desktop", "~/projets"]


def test_build_open_url_no_profile_uses_xdg_open() -> None:
    assert build_open_url_argv("https://ex.com", profile=None, browser="default") == [
        "xdg-open",
        "https://ex.com",
    ]


def test_build_open_url_chrome_profile() -> None:
    argv = build_open_url_argv("https://cal.google.com", profile="Perso", browser="chrome")
    assert argv == [
        "google-chrome",
        "--profile-directory=Perso",
        "https://cal.google.com",
    ]


def test_build_open_url_firefox_profile() -> None:
    argv = build_open_url_argv("https://ex.com", profile="Boulot", browser="firefox")
    assert argv == ["firefox", "-P", "Boulot", "https://ex.com"]


def test_build_open_url_chromium_profile() -> None:
    argv = build_open_url_argv("https://ex.com", profile="Dev", browser="chromium")
    assert argv == ["chromium", "--profile-directory=Dev", "https://ex.com"]


# ============================================================ faux runner (capture)
class FakeRunner:
    """Capture les argv et renvoie des réponses canned indexées par un motif d'argv."""

    def __init__(self, responses: dict[str, tuple[int, str, str]] | None = None) -> None:
        self.calls: list[list[str]] = []
        self._responses = responses or {}

    async def __call__(self, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        joined = " ".join(argv)
        for needle, resp in self._responses.items():
            if needle in joined:
                return resp
        return (0, "", "")


def _ext_absent() -> FakeRunner:
    # `gdbus introspect` échoue -> extension indisponible.
    return FakeRunner({"introspect": (1, "", "Error: name not found")})


def _ext_present() -> FakeRunner:
    return FakeRunner(
        {
            "introspect": (0, "node ...", ""),
            "GetCurrentState": (0, DISPLAY_STATE_SAMPLE, ""),
            "ListMonitors": (
                0,
                "([(0, 0, 0, 1920, 1080), (1, 1920, 0, 2560, 1440), (2, 4480, 0, 1920, 1080)],)",
                "",
            ),
            "MoveWindow": (0, "(true,)", ""),
            "FocusWindow": (0, "(true,)", ""),
            "CloseWindow": (0, "(true,)", ""),
        }
    )


async def test_launch_app_builds_gtk_launch_command() -> None:
    runner = FakeRunner()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = await desk.launch_app("code", ["~/x"])
    assert ref.app_id == "code"
    assert runner.calls[0] == ["gtk-launch", "code.desktop", "~/x"]


async def test_launch_app_falls_back_to_gio_launch() -> None:
    runner = FakeRunner({"gtk-launch": (1, "", "not found")})
    desk = GnomeWaylandDesktop(runner=runner)
    await desk.launch_app("weird")
    assert runner.calls[0][0] == "gtk-launch"
    assert runner.calls[1][:2] == ["gio", "launch"]


async def test_open_url_no_profile_runs_xdg_open() -> None:
    runner = FakeRunner()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = await desk.open_url("https://ex.com")
    assert runner.calls[0] == ["xdg-open", "https://ex.com"]
    assert ref.app_id == "xdg-open"


async def test_open_url_with_profile_runs_dedicated_browser() -> None:
    runner = FakeRunner()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = await desk.open_url("https://ex.com", profile="Perso", browser="chrome")
    assert runner.calls[0] == [
        "google-chrome",
        "--profile-directory=Perso",
        "https://ex.com",
    ]
    assert ref.app_id == "google-chrome"


async def test_list_screens_delegates_to_mutter() -> None:
    runner = FakeRunner({"GetCurrentState": (0, DISPLAY_STATE_SAMPLE, "")})
    desk = GnomeWaylandDesktop(runner=runner)
    screens = await desk.list_screens()
    assert [s.id for s in screens] == ["eDP-1", "HDMI-1", "DP-1"]
    assert runner.calls[0][0] == "gdbus"


# ============================================================ dégradation propre
async def test_move_window_degrades_without_extension() -> None:
    runner = _ext_absent()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = AppRef(app_id="code", pid=1234, window_id="42")
    res = await desk.move_window(ref, "eDP-1", Geometry(0, 0, 1280, 800))
    assert res.placed is False
    assert res.reason == "extension_unavailable"
    # Aucune commande de déplacement n'a été tentée.
    assert all("MoveWindow" not in " ".join(c) for c in runner.calls)


async def test_move_window_unknown_screen_when_extension_present() -> None:
    runner = _ext_present()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = AppRef(app_id="code", window_id="42")
    res = await desk.move_window(ref, "VGA-9", Geometry(0, 0, 800, 600))
    assert res.placed is False
    assert res.reason.startswith("unknown_screen")


async def test_move_window_places_via_extension() -> None:
    runner = _ext_present()
    desk = GnomeWaylandDesktop(runner=runner)
    ref = AppRef(app_id="code", window_id="42")
    res = await desk.move_window(ref, "HDMI-1", Geometry(1920, 0, 2560, 1440))
    assert res.placed is True
    move_calls = [c for c in runner.calls if "MoveWindow" in " ".join(c)]
    assert len(move_calls) == 1
    # monitor index 1 (HDMI-1) doit être passé, avec la géométrie demandée.
    assert "1" in move_calls[0]
    assert "2560" in move_calls[0] and "1440" in move_calls[0]


async def test_focus_noop_without_extension() -> None:
    runner = _ext_absent()
    desk = GnomeWaylandDesktop(runner=runner)
    await desk.focus(AppRef(app_id="code", window_id="42"))
    assert all("FocusWindow" not in " ".join(c) for c in runner.calls)


async def test_kill_app_falls_back_to_kill_signal() -> None:
    runner = _ext_absent()
    desk = GnomeWaylandDesktop(runner=runner)
    await desk.kill_app(AppRef(app_id="code", pid=4321))
    assert runner.calls[-1] == ["kill", "4321"]


async def test_kill_app_closes_via_extension_when_available() -> None:
    runner = _ext_present()
    desk = GnomeWaylandDesktop(runner=runner)
    await desk.kill_app(AppRef(app_id="code", window_id="42"))
    assert any("CloseWindow" in " ".join(c) for c in runner.calls)
    assert all(c[0] != "kill" for c in runner.calls)


# ============================================================ capacités
async def test_capabilities_without_extension() -> None:
    caps = await GnomeWaylandDesktop(runner=_ext_absent()).capabilities()
    assert caps.backend == "gnome-wayland"
    assert caps.can_launch is True
    assert caps.can_open_url is True
    assert caps.can_place_windows is False


async def test_capabilities_with_extension() -> None:
    caps = await GnomeWaylandDesktop(runner=_ext_present()).capabilities()
    assert caps.can_place_windows is True


# ============================================================ parsing retours extension
def test_parse_windows_sample() -> None:
    sample = (
        "([('42', 'code', 'main.py — VSCode', 0, 10, 20, 1280, 800), "
        "('7', 'firefox', 'Mozilla Firefox', 1, 1920, 0, 2560, 1440)],)"
    )
    windows = parse_windows(sample)
    assert [w.id for w in windows] == ["42", "7"]
    assert windows[0].wm_class == "code"
    assert windows[0].title == "main.py — VSCode"
    assert windows[1].monitor == 1
    assert windows[1].width == 2560


def test_parse_monitors_sample() -> None:
    sample = "([(0, 0, 0, 1920, 1080), (1, 1920, 0, 2560, 1440)],)"
    monitors = parse_monitors(sample)
    assert [m.index for m in monitors] == [0, 1]
    assert monitors[1].x == 1920 and monitors[1].width == 2560


def test_parse_string_return_empty_and_value() -> None:
    assert parse_string_return("('',)") == ""
    assert parse_string_return("('99',)") == "99"
