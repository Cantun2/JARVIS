"""Démo Phase 1 : joue la séquence de réveil ATLAS en mock et imprime le flux.

Aucun credential, aucun modèle, aucun matériel. Vérifie la séquence d'événements
canonique et sort en 0 si tout est cohérent.
"""

from __future__ import annotations

import asyncio
import sys

from jarvis.agents.atlas import AtlasInput
from jarvis.assembly import build_context
from jarvis.config import Settings
from jarvis.core.events import EventType
from jarvis.desktop.mock_desktop import MockDesktop
from jarvis.io.telegram import MockTelegram

_COLORS = {
    EventType.WAKE_UP: "\033[96m",
    EventType.PROFILE_LOADED: "\033[96m",
    EventType.DESKTOP_ACTION: "\033[90m",
    EventType.MAIL_RECEIVED: "\033[94m",
    EventType.MAIL_TRIAGED: "\033[93m",
    EventType.AGENT_STARTED: "\033[92m",
    EventType.AGENT_FINISHED: "\033[92m",
    EventType.AGENT_FAILED: "\033[91m",
    EventType.BRIEFING_READY: "\033[95m",
}
_RESET = "\033[0m"


def _c(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{_RESET}"


def _banner(title: str) -> None:
    line = "─" * 62
    print(_c(f"┌{line}┐", "\033[96m"))
    print(_c(f"│ {title:<60} │", "\033[96m"))
    print(_c(f"└{line}┘", "\033[96m"))


async def run_demo() -> int:
    ctx = build_context(Settings(mode="mock", db_path=":memory:"))
    _banner("JARVIS · Démo Phase 1 · Réveil (profil deep-work) · MODE MOCK")

    out = await ctx.runner.run_by_name("ATLAS", AtlasInput(profile="deep-work"))
    await ctx.bus.drain()

    print(_c("\n»  Flux d'événements (journal, ordre total)\n", "\033[1m"))
    for seq, event in ctx.journal.replay_with_seq():
        color = _COLORS.get(event.type, "\033[0m")
        ts = event.ts.strftime("%H:%M:%S")
        summary = _summarize(event.type, event.payload)
        print(
            f"  {seq:>3} {ts}  {_c(event.type.value.ljust(16), color)} {event.source:<8} {summary}"
        )

    assert isinstance(ctx.desktop, MockDesktop)
    assert isinstance(ctx.telegram, MockTelegram)

    print(_c("\n»  Actions desktop\n", "\033[1m"))
    for action in ctx.desktop.actions:
        print(f"    {action.kind:<12} {action.detail}")

    print(_c("\n»  Briefing ORACLE (poussé sur Telegram)\n", "\033[1m"))
    for msg in ctx.telegram.sent:
        print(f"    [{msg.level}] {msg.text}")

    status = ctx.journal.latest_status_by_agent()
    print(_c("\n»  Récapitulatif des runs\n", "\033[1m"))
    for name in ("ATLAS", "HERMES", "ORACLE"):
        s = status[name]
        print(f"    {name:<8} {s['status']:<10} tokens={s['tokens']:<6} usd={s['usd']}")

    ok = _check_sequence(ctx)
    print()
    if ok:
        print(_c("✓ Séquence de réveil cohérente. Démo OK.", "\033[92m"))
    else:
        print(_c("✗ Séquence incohérente.", "\033[91m"))
    ctx.close()
    return 0 if ok and out is not None else 1


def _summarize(etype: EventType, payload: dict[str, object]) -> str:
    if etype == EventType.WAKE_UP:
        return f"profil={payload.get('profile')}"
    if etype == EventType.PROFILE_LOADED:
        return (
            f"lancées={payload.get('launched')} "
            f"ouvertes={payload.get('opened')} placées={payload.get('placed')}"
        )
    if etype == EventType.DESKTOP_ACTION:
        return f"{payload.get('kind')} {payload.get('app_id') or payload.get('url') or ''}"
    if etype == EventType.MAIL_TRIAGED:
        return f"{payload.get('category')} (prio {payload.get('priority')})"
    if etype == EventType.BRIEFING_READY:
        text = str(payload.get("text", ""))
        return text[:60] + ("…" if len(text) > 60 else "")
    return ""


def _check_sequence(ctx: object) -> bool:
    from jarvis.assembly import JarvisContext

    assert isinstance(ctx, JarvisContext)
    types = [e.type for e in ctx.journal.replay()]
    try:
        return (
            types.index(EventType.WAKE_UP)
            < types.index(EventType.PROFILE_LOADED)
            < types.index(EventType.MAIL_TRIAGED)
            < types.index(EventType.BRIEFING_READY)
        )
    except ValueError:
        return False


async def run_demo_phase3() -> int:
    from jarvis.agents.daedalus import DaedalusInput, DaedalusOutput
    from jarvis.core.events import EventType as ET
    from jarvis.night.manager import NightShiftManager

    ctx = build_context(Settings(mode="mock", db_path=":memory:"))
    _banner("JARVIS · Démo Phase 3 · La nuit (DAEDALUS + dry-run) · MOCK")

    out = await ctx.runner.run_by_name(
        "DAEDALUS",
        DaedalusInput(goal="Ajouter un tableau de bord de stats", project_name="Reporting"),
    )
    assert isinstance(out, DaedalusOutput)
    project_id = out.project_id
    report = await NightShiftManager(ctx.tasks, ctx.bus, ctx.settings).run_night(project_id)
    await ctx.bus.drain()

    print(_c("\n»  Backlog généré par DAEDALUS\n", "\033[1m"))
    for task in ctx.tasks.list_tasks(project_id):
        print(f"    [{task.status.value:<11}] {task.title}")

    print(_c("\n»  Night Report (dry-run)\n", "\033[1m"))
    print(
        f"    done={report.done}  blocked={report.blocked}  failed={report.failed}  "
        f"coût={report.cost_usd}€  dry_run={report.dry_run}"
    )
    for blocker in report.blockers:
        print(f"    ⚠ {blocker}")

    types = [e.type for e in ctx.journal.replay()]
    ok = (
        ET.BACKLOG_READY in types
        and types.index(ET.BACKLOG_READY)
        < types.index(ET.TASK_TRANSITIONED)
        < types.index(ET.NIGHT_REPORT_READY)
    )
    print()
    if ok:
        print(_c("✓ Nuit dry-run cohérente (VULCAN resté désarmé). Démo OK.", "\033[92m"))
    else:
        print(_c("✗ Séquence nocturne incohérente.", "\033[91m"))
    ctx.close()
    return 0 if ok else 1


def main() -> int:
    return asyncio.run(run_demo())


def main_phase3() -> int:
    return asyncio.run(run_demo_phase3())


if __name__ == "__main__":
    sys.exit(main())
