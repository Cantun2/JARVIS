"""Chargement/validation des Day Profiles depuis des fichiers TOML."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from jarvis.core.errors import JarvisError
from jarvis.profiles.models import DayProfile

# Répertoire des profils livrés (racine du repo / profiles).
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parents[3] / "profiles"


class ProfileError(JarvisError):
    """Profil introuvable ou invalide."""


def load_profile(name_or_path: str, *, directory: Path | None = None) -> DayProfile:
    """Charge un profil par nom (`deep-work`) ou par chemin de fichier."""
    path = Path(name_or_path)
    if not path.suffix:
        base = directory or DEFAULT_PROFILE_DIR
        path = base / f"{name_or_path}.toml"
    if not path.is_file():
        raise ProfileError(f"Profil introuvable : {path}")
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"TOML invalide dans {path} : {exc}") from exc
    data.setdefault("name", path.stem)
    try:
        return DayProfile.model_validate(data)
    except ValidationError as exc:
        raise ProfileError(f"Profil invalide {path} :\n{exc}") from exc


def list_profiles(directory: Path | None = None) -> list[str]:
    base = directory or DEFAULT_PROFILE_DIR
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.glob("*.toml"))
