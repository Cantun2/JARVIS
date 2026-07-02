"""AgentRunner : cycle de vie, gating des capacités, escalade, désarmement, trigger."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from jarvis.core.bus import EventBus
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, AgentInput, AgentOutput, Permission
from jarvis.core.errors import AgentDisarmed, EscalationRequired, PermissionDenied
from jarvis.core.events import EventType
from jarvis.core.journal import SQLiteJournal
from jarvis.core.orchestrator import AgentRunner
from jarvis.core.registry import AgentRegistry

RunFn = Callable[[AgentInput, AgentContext], Awaitable[AgentOutput]]


class _In(AgentInput):
    x: int = 0


class _Out(AgentOutput):
    y: int = 0


class _Agent:
    def __init__(self, contract: AgentContract, run_fn: RunFn) -> None:
        self._contract = contract
        self._run_fn = run_fn

    @property
    def contract(self) -> AgentContract:
        return self._contract

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        return await self._run_fn(data, ctx)


def _make(
    name: str,
    run_fn: RunFn,
    *,
    permissions: tuple[Permission, ...] = (),
    enabled: bool = True,
) -> _Agent:
    contract = AgentContract(
        name=name,
        mode="on_demand",
        permissions=permissions,
        inputs=_In,
        outputs=_Out,
        enabled=enabled,
    )
    return _Agent(contract, run_fn)


def _types(journal: SQLiteJournal) -> list[EventType]:
    return [e.type for e in journal.replay()]


async def test_happy_path_emits_started_then_finished(
    runner: AgentRunner, journal: SQLiteJournal
) -> None:
    async def run_fn(data: _In, ctx: AgentContext) -> _Out:  # type: ignore[override]
        return _Out(y=data.x + 1)

    out = await runner.run(_make("echo", run_fn), _In(x=41))
    assert isinstance(out, _Out) and out.y == 42
    assert _types(journal) == [EventType.AGENT_STARTED, EventType.AGENT_FINISHED]
    assert journal.latest_status_by_agent()["echo"]["status"] == "finished"


async def test_capability_gating(bus: EventBus, enforcer, registry: AgentRegistry) -> None:  # type: ignore[no-untyped-def]
    gw, dsk, tg = object(), object(), object()
    runner = AgentRunner(bus, enforcer, registry, gateway=gw, desktop=dsk, telegram=tg)
    captured: dict[str, object | None] = {}

    async def run_fn(_d: _In, ctx: AgentContext) -> _Out:
        captured["gateway"] = ctx.gateway
        captured["desktop"] = ctx.desktop
        captured["telegram"] = ctx.telegram
        return _Out()

    # N'a QUE desktop.launch → desktop injecté, gateway/telegram = None
    await runner.run(_make("d", run_fn, permissions=(Permission.DESKTOP_LAUNCH,)), _In())
    assert captured == {"gateway": None, "desktop": dsk, "telegram": None}


async def test_mail_capability_gating(bus: EventBus, enforcer, registry: AgentRegistry) -> None:  # type: ignore[no-untyped-def]
    mail_sentinel = object()
    runner = AgentRunner(bus, enforcer, registry, mail=mail_sentinel)
    captured: dict[str, object | None] = {}

    async def run_fn(_d: _In, ctx: AgentContext) -> _Out:
        captured["mail"] = ctx.mail
        return _Out()

    await runner.run(_make("reader", run_fn, permissions=(Permission.MAIL_READ,)), _In())
    assert captured["mail"] is mail_sentinel

    captured.clear()
    await runner.run(_make("blind", run_fn), _In())  # sans MAIL_READ → None
    assert captured["mail"] is None


async def test_require_capability_raises_when_absent(runner: AgentRunner) -> None:
    async def run_fn(_d: _In, ctx: AgentContext) -> _Out:
        ctx.require_gateway()  # pas de permission → PermissionDenied
        return _Out()

    with pytest.raises(PermissionDenied):
        await runner.run(_make("nogw", run_fn), _In())


async def test_disarmed_agent_refuses(runner: AgentRunner, journal: SQLiteJournal) -> None:
    async def run_fn(_d: _In, _c: AgentContext) -> _Out:
        return _Out()

    with pytest.raises(AgentDisarmed):
        await runner.run(_make("vulcan", run_fn, enabled=False), _In())
    assert _types(journal) == [EventType.AGENT_FAILED]


async def test_permission_denied_path(runner: AgentRunner, journal: SQLiteJournal) -> None:
    async def run_fn(_d: _In, _c: AgentContext) -> _Out:
        return _Out()

    agent = _make("bad", run_fn, permissions=(Permission.MAIL_SEND,))
    with pytest.raises(PermissionDenied):
        await runner.run(agent, _In())
    assert _types(journal) == [EventType.PERMISSION_DENIED]


async def test_escalation_emits_event_and_raises(
    runner: AgentRunner, journal: SQLiteJournal
) -> None:
    async def run_fn(_d: _In, _c: AgentContext) -> _Out:
        raise EscalationRequired("Merger la PR ?", options=["oui", "non"])

    with pytest.raises(EscalationRequired):
        await runner.run(_make("daedalus", run_fn), _In())
    assert _types(journal) == [EventType.AGENT_STARTED, EventType.AGENT_ESCALATED]
    assert journal.latest_status_by_agent()["daedalus"]["status"] == "escalated"


async def test_failure_is_recorded(runner: AgentRunner, journal: SQLiteJournal) -> None:
    async def run_fn(_d: _In, _c: AgentContext) -> _Out:
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        await runner.run(_make("flaky", run_fn), _In())
    assert _types(journal) == [EventType.AGENT_STARTED, EventType.AGENT_FAILED]


async def test_agent_can_emit_and_trigger_another(
    runner: AgentRunner, registry: AgentRegistry, journal: SQLiteJournal
) -> None:
    async def child_fn(_d: _In, ctx: AgentContext) -> _Out:
        await ctx.emit(EventType.MAIL_TRIAGED, count=3)
        return _Out(y=7)

    child = _make("child", child_fn)
    registry.register(child)

    async def parent_fn(_d: _In, ctx: AgentContext) -> _Out:
        await ctx.emit(EventType.WAKE_UP)
        res = await ctx.trigger("child", _In(x=1))
        assert isinstance(res, _Out) and res.y == 7
        return _Out(y=0)

    await runner.run(_make("parent", parent_fn), _In())
    # Ordre attendu : parent démarre, émet wake_up, enfant démarre, triage, enfant fini, parent fini
    assert _types(journal) == [
        EventType.AGENT_STARTED,
        EventType.WAKE_UP,
        EventType.AGENT_STARTED,
        EventType.MAIL_TRIAGED,
        EventType.AGENT_FINISHED,
        EventType.AGENT_FINISHED,
    ]
