"""Configuration du logging structuré (structlog)."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_configured = False


def configure_logging(*, level: str = "INFO", json_logs: bool | None = None) -> None:
    """Configure structlog une seule fois. JSON si stdout n'est pas un terminal."""
    global _configured
    if _configured:
        return
    if json_logs is None:
        json_logs = not sys.stdout.isatty()

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str, **initial: Any) -> structlog.stdlib.BoundLogger:
    """Retourne un logger lié, en s'assurant que structlog est configuré."""
    if not _configured:
        configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name, **initial)
    return logger
