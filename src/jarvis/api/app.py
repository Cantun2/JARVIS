"""Application FastAPI : composition root + montage des routes et du WebSocket."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from jarvis import __version__
from jarvis.api import (
    routes_agents,
    routes_chat,
    routes_events,
    routes_projects,
    routes_todo,
    routes_voice,
)
from jarvis.api.ws import WsHub, websocket_endpoint
from jarvis.assembly import JarvisContext, build_context
from jarvis.config import Settings, get_settings
from jarvis.logging import get_logger
from jarvis.scheduler import ReminderScheduler

log = get_logger("jarvis.api")

# Origines autorisées en dev (UI Vite).
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:1420",  # Tauri dev
]


def create_app(context: JarvisContext | None = None) -> FastAPI:
    """Construit l'app. `context` injectable pour les tests ; sinon assemblé au démarrage."""
    owns_context = context is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx = context or build_context()
        hub = WsHub(ctx)
        hub.start()
        scheduler = ReminderScheduler(ctx)
        scheduler.start()
        app.state.ctx = ctx
        app.state.ws_hub = hub
        app.state.scheduler = scheduler
        log.info(
            "api_ready",
            mode=ctx.settings.mode,
            inference=ctx.gateway.backend_name,
        )
        try:
            yield
        finally:
            scheduler.stop()
            hub.stop()
            if owns_context:
                ctx.close()

    app = FastAPI(title="jarvis-suit", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_agents.router, prefix="/api")
    app.include_router(routes_events.router, prefix="/api")
    app.include_router(routes_projects.router, prefix="/api")
    app.include_router(routes_voice.router, prefix="/api")
    app.include_router(routes_chat.router, prefix="/api")
    app.include_router(routes_todo.router, prefix="/api")
    app.add_api_websocket_route("/ws", websocket_endpoint)
    _mount_ui(app, context.settings if context else get_settings())
    return app


def _mount_ui(app: FastAPI, settings: Settings) -> None:
    """Sert l'UI buildée (produit mono-processus) si JARVIS_UI_DIST pointe un dossier.

    Monté **en dernier**, sur "/", pour que /api et /ws (enregistrés avant) l'emportent.
    En mode dev (ui_dist=None), on ne monte rien : l'UI est servie par Vite avec proxy.
    """
    if not settings.ui_dist:
        return
    dist = Path(settings.ui_dist)
    if not dist.is_dir():
        log.warning("ui_dist_absent", path=str(dist))
        return
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
    log.info("ui_mounted", path=str(dist))
