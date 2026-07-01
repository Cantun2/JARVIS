"""Night Report factice pour ORACLE (ce que VULCAN aurait fait cette nuit)."""

from __future__ import annotations

from pydantic import BaseModel


class NightTask(BaseModel):
    title: str
    status: str  # done | blocked | failed
    branch: str | None = None
    note: str = ""


class NightReport(BaseModel):
    date: str
    done: int
    blocked: int
    failed: int
    cost_usd: float
    tasks: tuple[NightTask, ...]
    blockers: tuple[str, ...]


MOCK_NIGHT_REPORT = NightReport(
    date="2026-07-01",
    done=4,
    blocked=1,
    failed=0,
    cost_usd=0.42,
    tasks=(
        NightTask(
            title="Ajouter la pagination à l'API events", status="done", branch="night/pagination"
        ),
        NightTask(title="Corriger le flaky test du bus", status="done", branch="night/fix-flaky"),
        NightTask(
            title="Documenter le module profiles", status="done", branch="night/docs-profiles"
        ),
        NightTask(title="Migrer le journal vers Postgres", status="done", branch="night/pg"),
        NightTask(
            title="Choisir la lib de graphes pour le HUD",
            status="blocked",
            note="Recharts ou visx ? Décision d'archi requise.",
        ),
    ),
    blockers=("Tâche « lib de graphes » : Recharts ou visx ? J'attends ta décision.",),
)
