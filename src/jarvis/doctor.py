"""Diagnostic d'environnement : outils présents/absents, mode effectif.

Lecture seule, aucun réseau. Aide à savoir ce qui tourne en mock vs réel.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys

from jarvis.config import get_settings
from jarvis.inference.factory import build_backend

_SYSTEM_TOOLS = {
    "gio": "lancement d'apps (desktop réel)",
    "gtk-launch": "lancement d'apps (desktop réel)",
    "gdbus": "topologie écrans + extension GNOME",
    "xdg-open": "ouverture d'URL",
    "gnome-extensions": "installer l'extension de placement",
    "docker": "sandbox VULCAN (plus tard)",
    "ollama": "inférence locale (optionnel)",
    "uv": "gestion des dépendances OpenJarvis",
    "cargo": "build natif OpenJarvis / packaging Tauri",
    "node": "UI (Vite)",
    "npm": "UI (Vite)",
    "claude": "VULCAN headless (plus tard)",
}

_PY_PACKAGES = {
    "openjarvis": "backend d'inférence réel (extra [openjarvis])",
    "anthropic": "inférence cloud (extra [cloud])",
    "ollama": "client Ollama (extra [local])",
    "googleapiclient": "API Gmail réelle (extra [google])",
}


def _ok(present: bool) -> str:
    mark = "✓" if present else "✗"
    color = "\033[92m" if present else "\033[90m"
    if not sys.stdout.isatty():
        return mark
    return f"{color}{mark}\033[0m"


def main() -> int:
    settings = get_settings()
    print("JARVIS · doctor\n")
    print(f"  Mode effectif        : {settings.mode}")
    print(f"  Backend inférence     : {build_backend(settings).name}")
    print(f"  URL Ollama            : {settings.ollama_url or '—'} (modèle {settings.local_model})")
    print(f"  URL inférence (OpenAI): {settings.inference_url or '—'}")
    print(f"  Backend desktop       : {settings.desktop_backend}")
    print(f"  Backend mails         : {settings.mail_backend}")
    print(f"  Token OAuth Gmail     : {'défini' if settings.gmail_token_path else '—'}")
    print(f"  Clé Anthropic         : {'définie' if settings.anthropic_api_key else '—'}")
    print(f"  Token Telegram        : {'défini' if settings.telegram_bot_token else '—'}")

    print("\n  Outils système :")
    for tool, why in _SYSTEM_TOOLS.items():
        present = shutil.which(tool) is not None
        print(f"    {_ok(present)} {tool:<16} {why}")

    print("\n  Paquets Python optionnels :")
    for pkg, why in _PY_PACKAGES.items():
        present = importlib.util.find_spec(pkg) is not None
        print(f"    {_ok(present)} {pkg:<16} {why}")

    print(
        "\n  → En mode mock, aucun de ces éléments n'est requis. "
        "Voir docs/MANUAL_SETUP.md pour brancher le réel."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
