"""Modèles d'un Day Profile + parsing du DSL court des applications.

Exemples de DSL :
  "terminal"                                  → kind=terminal
  "vscode:~/projets/x"                        → kind=vscode, target=~/projets/x
  "chrome:profile=perso:tabs=[calendar,gmail]" → kind=chrome, profile=perso, tabs=(...)
  "spotify:playlist=focus"                    → kind=spotify, params={playlist: focus}
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


def parse_app_spec(raw: str) -> dict[str, Any]:
    """Transforme la chaîne DSL en dict validable par `AppSpec`."""
    parts = [p.strip() for p in raw.split(":")]
    kind = parts[0]
    target: str | None = None
    profile: str | None = None
    tabs: tuple[str, ...] = ()
    params: dict[str, str] = {}
    for seg in parts[1:]:
        if not seg:
            continue
        if "=" in seg:
            key, val = (s.strip() for s in seg.split("=", 1))
            if val.startswith("[") and val.endswith("]"):
                items = tuple(x.strip() for x in val[1:-1].split(",") if x.strip())
                if key == "tabs":
                    tabs = items
                else:
                    params[key] = val
            elif key == "profile":
                profile = val
            else:
                params[key] = val
        elif target is None:
            target = seg
        else:
            params.setdefault("arg", seg)
    return {
        "kind": kind,
        "target": target,
        "profile": profile,
        "tabs": tabs,
        "params": params,
        "raw": raw,
    }


class AppSpec(BaseModel):
    """Une application à lancer/ouvrir. Accepte une chaîne DSL en entrée."""

    model_config = ConfigDict(frozen=True)

    kind: str
    target: str | None = None
    profile: str | None = None
    tabs: tuple[str, ...] = ()
    params: dict[str, str] = {}
    raw: str = ""

    @model_validator(mode="before")
    @classmethod
    def _accept_dsl(cls, data: Any) -> Any:
        if isinstance(data, str):
            return parse_app_spec(data)
        return data


class LayoutSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    screen_1: tuple[AppSpec, ...] = ()
    screen_2: tuple[AppSpec, ...] = ()
    screen_3: tuple[AppSpec, ...] = ()

    def screens(self) -> list[tuple[int, tuple[AppSpec, ...]]]:
        """Écrans non vides, avec leur index 1-based."""
        return [
            (i, specs)
            for i, specs in enumerate((self.screen_1, self.screen_2, self.screen_3), start=1)
            if specs
        ]


class AppsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launch: tuple[AppSpec, ...] = ()
    kill: tuple[str, ...] = ()


class BriefingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice: bool = False
    include: tuple[str, ...] = ()


class FocusSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    do_not_disturb: bool = False


class DayProfile(BaseModel):
    """Profil de journée complet. `name` est injecté par le loader (nom de fichier)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    layout: LayoutSpec = LayoutSpec()
    apps: AppsSpec = AppsSpec()
    briefing: BriefingSpec = BriefingSpec()
    focus: FocusSpec = FocusSpec()
