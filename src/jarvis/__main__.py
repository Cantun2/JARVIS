"""Point d'entrée CLI : `python -m jarvis <serve|demo|doctor>`."""

from __future__ import annotations

import argparse
import sys

from jarvis import __version__
from jarvis.config import get_settings


def _serve() -> int:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "jarvis.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis-suit", description="Assistant JARVIS")
    parser.add_argument("--version", action="version", version=f"jarvis-suit {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="Lance l'API + WebSocket")
    sub.add_parser("demo", help="Joue la séquence de réveil en mock")
    sub.add_parser("doctor", help="Diagnostique l'environnement")

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve()
    if args.command == "demo":
        from jarvis.demo import main as demo_main

        return demo_main()
    if args.command == "doctor":
        from jarvis.doctor import main as doctor_main

        return doctor_main()
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
