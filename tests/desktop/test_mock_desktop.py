"""MockDesktop : 3 écrans simulés, enregistrement des actions, placement gaté."""

from __future__ import annotations

from jarvis.desktop.controller import AppRef, Geometry
from jarvis.desktop.mock_desktop import MockDesktop


async def test_three_screens_by_default() -> None:
    screens = await MockDesktop().list_screens()
    assert [s.id for s in screens] == ["screen-1", "screen-2", "screen-3"]
    assert screens[0].primary is True


async def test_launch_records_action_and_returns_ref() -> None:
    d = MockDesktop()
    ref = await d.launch_app("code.desktop", ["~/projets/x"])
    assert ref.app_id == "code.desktop" and ref.pid is not None
    assert d.kinds() == ["launch_app"]
    assert d.actions[0].detail["args"] == ["~/projets/x"]


async def test_open_url_carries_profile() -> None:
    d = MockDesktop()
    await d.open_url("https://calendar.google.com", profile="perso", browser="chrome")
    assert d.actions[0].detail["profile"] == "perso"
    assert d.actions[0].detail["browser"] == "chrome"


async def test_move_window_to_known_screen_is_placed() -> None:
    d = MockDesktop()
    ref = AppRef(app_id="code", pid=1, window_id="w1")
    res = await d.move_window(ref, "screen-2", Geometry(1920, 0, 1280, 1440))
    assert res.placed is True


async def test_move_window_to_unknown_screen_degrades() -> None:
    d = MockDesktop()
    ref = AppRef(app_id="code", pid=1, window_id="w1")
    res = await d.move_window(ref, "screen-9")
    assert res.placed is False and "inconnu" in res.reason


async def test_capabilities() -> None:
    caps = await MockDesktop().capabilities()
    assert caps.backend == "mock" and caps.can_place_windows is True
