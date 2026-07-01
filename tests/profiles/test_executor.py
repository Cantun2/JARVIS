"""ProfileExecutor : kill → launch → open → placement, sur MockDesktop."""

from __future__ import annotations

from jarvis.desktop.controller import DesktopAction
from jarvis.desktop.mock_desktop import MockDesktop
from jarvis.profiles.executor import ProfileExecutor
from jarvis.profiles.loader import load_profile


async def test_apply_deepwork_produces_expected_actions() -> None:
    desktop = MockDesktop()
    seen: list[str] = []

    async def on_action(a: DesktopAction) -> None:
        seen.append(a.kind)

    result = await ProfileExecutor(desktop, on_action).apply(load_profile("deep-work"))

    # kill discord+steam, spotify lancé globalement, vscode/terminal/obsidian lancés,
    # chrome ouvre calendar+gmail (écran 2) + github (écran 3).
    assert result.killed == 2
    assert result.opened == 3  # calendar, gmail, github
    assert result.launched >= 4  # spotify, vscode, terminal, obsidian
    # tout ce qui est sur un écran est placé (MockDesktop connaît 3 écrans)
    assert result.unplaced == 0 and result.placed > 0
    # le callback a bien reçu chaque action
    assert seen == [a.kind for a in result.actions]
    assert "kill_app" in seen and "open_url" in seen and "move_window" in seen


async def test_kill_happens_before_launch() -> None:
    desktop = MockDesktop()
    result = await ProfileExecutor(desktop).apply(load_profile("deep-work"))
    first_kill = next(i for i, a in enumerate(result.actions) if a.kind == "kill_app")
    first_launch = next(i for i, a in enumerate(result.actions) if a.kind == "launch_app")
    assert first_kill < first_launch


async def test_open_url_resolves_aliases() -> None:
    desktop = MockDesktop()
    await ProfileExecutor(desktop).apply(load_profile("default"))
    urls = [a.detail["url"] for a in desktop.actions if a.kind == "open_url"]
    assert "https://mail.google.com" in urls
    assert "https://calendar.google.com" in urls


async def test_fewer_screens_falls_back_to_primary() -> None:
    # Un seul écran physique : les apps de screen_2/3 retombent sur l'écran primaire.
    from jarvis.desktop.controller import Geometry, Screen

    solo = MockDesktop([Screen("screen-1", "laptop", Geometry(0, 0, 1920, 1080), primary=True)])
    result = await ProfileExecutor(solo).apply(load_profile("deep-work"))
    assert result.unplaced == 0  # tout est placé sur l'écran primaire, rien d'orphelin
