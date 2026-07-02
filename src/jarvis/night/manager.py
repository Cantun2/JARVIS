"""NightShiftManager — simulation nocturne **dry-run** (VULCAN reste désarmé).

Fait progresser des tâches du backlog vers « review » (ou « blocked ») avec des rapports
et diffs FACTICES, respecte les budgets nuit, émet les événements, et produit un Night
Report. N'exécute AUCUNE commande shell/git : c'est une simulation pure.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from jarvis.config import Settings
from jarvis.core.bus import EventBus
from jarvis.core.events import Event, EventType, uuid7
from jarvis.night.models import NightReport, NightTask, TaskStatus
from jarvis.night.store import TaskStore

_COST_PER_TASK = 0.05  # coût simulé par tâche (dry-run)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "tache"


def _fake_diff(title: str) -> str:
    return (
        f"--- a/module.py\n+++ b/module.py\n"
        f"@@\n+# {title}\n+def feature():\n+    return True  # (dry-run simulé)\n"
    )


def _today() -> str:
    return datetime.now(tz=UTC).date().isoformat()


class NightShiftManager:
    """Simulateur dry-run du Night Shift. Ne pilote pas VULCAN, n'exécute rien."""

    def __init__(self, store: TaskStore, bus: EventBus, settings: Settings) -> None:
        self._store = store
        self._bus = bus
        self._settings = settings

    async def _emit(self, etype: EventType, corr: str, payload: dict[str, object]) -> None:
        await self._bus.publish(
            Event(type=etype, source="night-shift", correlation_id=corr, payload=payload)
        )

    async def run_night(self, project_id: str) -> NightReport:
        corr = uuid7()
        backlog = [t for t in self._store.list_tasks(project_id) if t.status == TaskStatus.BACKLOG][
            : self._settings.max_tasks_night
        ]

        done = blocked = 0
        cost = 0.0
        night_tasks: list[NightTask] = []
        blockers: list[str] = []

        for i, task in enumerate(backlog):
            if (
                self._settings.max_usd_night
                and cost + _COST_PER_TASK > self._settings.max_usd_night
            ):
                break
            cost += _COST_PER_TASK
            branch = f"night/{_slug(task.title)}"

            self._store.transition(task.id, TaskStatus.IN_PROGRESS)
            await self._emit(
                EventType.TASK_TRANSITIONED,
                corr,
                {
                    "task_id": task.id,
                    "project_id": project_id,
                    "from": "backlog",
                    "to": "in_progress",
                    "title": task.title,
                },
            )

            if i % 4 == 3:  # une tâche sur quatre nécessite une décision humaine
                question = f"Décision requise pour « {task.title} » : quelle approche retenir ?"
                self._store.transition(task.id, TaskStatus.BLOCKED, blocker=question)
                blocked += 1
                blockers.append(question)
                night_tasks.append(
                    NightTask(title=task.title, status="blocked", branch=branch, note=question)
                )
                await self._emit(
                    EventType.TASK_TRANSITIONED,
                    corr,
                    {
                        "task_id": task.id,
                        "project_id": project_id,
                        "from": "in_progress",
                        "to": "blocked",
                        "title": task.title,
                    },
                )
            else:
                task_report = f"Simulé (dry-run) : « {task.title} » implémentée, 3 tests passés."
                self._store.transition(
                    task.id, TaskStatus.REVIEW, report=task_report, diff=_fake_diff(task.title)
                )
                done += 1
                night_tasks.append(
                    NightTask(
                        title=task.title, status="done", branch=branch, note="En attente de review"
                    )
                )
                await self._emit(
                    EventType.TASK_TRANSITIONED,
                    corr,
                    {
                        "task_id": task.id,
                        "project_id": project_id,
                        "from": "in_progress",
                        "to": "review",
                        "title": task.title,
                    },
                )

        report = NightReport(
            date=_today(),
            done=done,
            blocked=blocked,
            failed=0,
            cost_usd=round(cost, 2),
            tasks=tuple(night_tasks),
            blockers=tuple(blockers),
            dry_run=True,
        )
        self._store.save_night_report(project_id, report)
        await self._emit(
            EventType.NIGHT_REPORT_READY,
            corr,
            {
                "project_id": project_id,
                "done": done,
                "blocked": blocked,
                "failed": 0,
                "cost_usd": report.cost_usd,
                "dry_run": True,
            },
        )
        return report
