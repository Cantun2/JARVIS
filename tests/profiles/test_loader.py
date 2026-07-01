"""Loader + parsing DSL des Day Profiles."""

from __future__ import annotations

import pytest

from jarvis.profiles.loader import ProfileError, list_profiles, load_profile
from jarvis.profiles.models import AppSpec, parse_app_spec


def test_parse_simple_kind() -> None:
    spec = AppSpec.model_validate("terminal")
    assert spec.kind == "terminal" and spec.target is None


def test_parse_target() -> None:
    spec = AppSpec.model_validate("vscode:~/projets/x")
    assert spec.kind == "vscode" and spec.target == "~/projets/x"


def test_parse_profile_and_tabs() -> None:
    spec = AppSpec.model_validate("chrome:profile=perso:tabs=[calendar,gmail]")
    assert spec.kind == "chrome"
    assert spec.profile == "perso"
    assert spec.tabs == ("calendar", "gmail")


def test_parse_params() -> None:
    assert parse_app_spec("spotify:playlist=focus")["params"] == {"playlist": "focus"}


def test_load_deepwork_profile() -> None:
    profile = load_profile("deep-work")
    assert profile.name == "deep-work"
    assert profile.focus.do_not_disturb is True
    assert profile.apps.kill == ("discord", "steam")
    # 3 écrans renseignés
    assert [i for i, _ in profile.layout.screens()] == [1, 2, 3]
    # premier de screen_2 = chrome perso avec 2 onglets
    chrome = profile.layout.screen_2[0]
    assert chrome.kind == "chrome" and chrome.tabs == ("calendar", "gmail")


def test_default_profile_loads() -> None:
    assert load_profile("default").name == "default"


def test_unknown_profile_raises() -> None:
    with pytest.raises(ProfileError, match="introuvable"):
        load_profile("nexiste-pas")


def test_list_profiles_includes_shipped() -> None:
    names = list_profiles()
    assert "deep-work" in names and "default" in names
