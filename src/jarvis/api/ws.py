"""WebSocket hub : relaie les événements du bus vers les clients connectés."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import WebSocket, WebSocketDisconnect

from jarvis.api.views import build_snapshot
from jarvis.assembly import JarvisContext
from jarvis.core.events import Event
from jarvis.logging import get_logger

log = get_logger("jarvis.ws")


class WsHub:
    """Diffuse chaque événement du bus à tous les WebSockets ouverts."""

    def __init__(self, ctx: JarvisContext) -> None:
        self._ctx = ctx
        self._conns: set[WebSocket] = set()
        self._unsub: Callable[[], None] | None = None

    def start(self) -> None:
        self._unsub = self._ctx.bus.subscribe(self._on_event, name="ws-hub")

    def stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        self._conns.clear()

    def add(self, ws: WebSocket) -> None:
        self._conns.add(ws)

    def remove(self, ws: WebSocket) -> None:
        self._conns.discard(ws)

    async def _on_event(self, event: Event) -> None:
        seq = self._ctx.bus.journal.seq_of(event.id) or 0
        message = {"kind": "event", "event": {"seq": seq, **event.to_wire()}}
        for ws in list(self._conns):
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError):
                self._conns.discard(ws)


async def websocket_endpoint(websocket: WebSocket) -> None:
    ctx: JarvisContext = websocket.app.state.ctx
    hub: WsHub = websocket.app.state.ws_hub
    await websocket.accept()
    await websocket.send_json(build_snapshot(ctx))
    hub.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # on ignore l'entrée, sert de keep-alive
    except WebSocketDisconnect:
        hub.remove(websocket)
