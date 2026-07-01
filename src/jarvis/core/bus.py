"""Event bus in-process (asyncio pub/sub), journal-first.

`publish` écrit d'abord dans le journal (durabilité), puis diffuse aux abonnés
sans bloquer. Un handler qui plante est isolé et loggé — il ne casse pas le bus.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field

from jarvis.core.events import Event, EventType
from jarvis.core.journal import SQLiteJournal
from jarvis.logging import get_logger

Handler = Callable[[Event], Awaitable[None]]
log = get_logger("jarvis.bus")


@dataclass
class _Subscription:
    handler: Handler
    types: frozenset[EventType] | None  # None = tous les types
    name: str


@dataclass
class EventBus:
    """Bus pub/sub. Le journal est la source de vérité ; le bus est le transport."""

    journal: SQLiteJournal
    _subs: list[_Subscription] = field(default_factory=list)
    _tasks: set[asyncio.Task[None]] = field(default_factory=set)

    def subscribe(
        self,
        handler: Handler,
        *,
        types: Iterable[EventType] | None = None,
        name: str = "anon",
    ) -> Callable[[], None]:
        """Abonne un handler. Retourne une fonction de désabonnement."""
        sub = _Subscription(
            handler=handler,
            types=frozenset(types) if types is not None else None,
            name=name,
        )
        self._subs.append(sub)

        def unsubscribe() -> None:
            if sub in self._subs:
                self._subs.remove(sub)

        return unsubscribe

    async def publish(self, event: Event) -> int:
        """Persiste puis diffuse l'événement. Retourne le `seq` du journal."""
        seq = self.journal.append(event)
        for sub in list(self._subs):
            if sub.types is None or event.type in sub.types:
                task = asyncio.create_task(self._dispatch(sub, event))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
        return seq

    async def _dispatch(self, sub: _Subscription, event: Event) -> None:
        try:
            await sub.handler(event)
        except Exception:
            log.exception("handler_failed", handler=sub.name, event_type=event.type.value)

    async def drain(self) -> None:
        """Attend la fin des handlers en cours (utile pour la démo/tests déterministes)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
