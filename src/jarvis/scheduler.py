"""ReminderScheduler — tâche de fond qui déclenche CHRONOS quand des rappels sont dus.

Première vraie tâche de fond de l'app (démarrée dans le lifespan FastAPI, à côté du WsHub).
Boucle résiliente : ne meurt jamais sur exception ; no-op si l'agenda est vide (zéro bruit).
La déduplication vit dans le store (`reminded_ts`), pas dans la boucle.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime

from jarvis.agents.chronos import ChronosInput
from jarvis.assembly import JarvisContext
from jarvis.logging import get_logger
from jarvis.todo.models import TodoKind

log = get_logger("jarvis.scheduler")


class ReminderScheduler:
    def __init__(self, ctx: JarvisContext) -> None:
        self._ctx = ctx
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if not self._ctx.settings.scheduler_enabled:
            log.info("scheduler_disabled")
            return
        self._task = asyncio.create_task(self._loop(), name="reminder-scheduler")

    def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        interval = self._ctx.settings.scheduler_interval_s
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                log.exception("scheduler_tick_failed")  # ne jamais laisser mourir la boucle
            # Attend l'intervalle, sauf si un stop est demandé entre-temps.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=interval)

    async def _tick(self) -> None:
        now = datetime.now()
        default_hour = self._ctx.settings.scheduler_default_remind_hour
        due = self._ctx.todos.due_reminders(now.isoformat(), default_hour=default_hour)
        if not due:
            return  # agenda vide / rien de dû → aucun appel, aucun bruit
        task_ids = tuple(t.id for t in due if t.kind is TodoKind.TASK)
        appt_ids = tuple(t.id for t in due if t.kind is TodoKind.APPOINTMENT)
        await self._ctx.runner.run_by_name(
            "CHRONOS",
            ChronosInput(trigger="scheduled", due_ids=task_ids, appointment_ids=appt_ids),
        )
