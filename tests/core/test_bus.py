"""Bus : journal-first, filtrage par type, isolation des handlers défaillants."""

from __future__ import annotations

from jarvis.core.bus import EventBus
from jarvis.core.events import Event, EventType, make_event
from jarvis.core.journal import SQLiteJournal


async def test_publish_is_journal_first(bus: EventBus, journal: SQLiteJournal) -> None:
    seen: list[int] = []

    async def handler(_e: Event) -> None:
        # Au moment où le handler tourne, l'événement est déjà durable.
        seen.append(journal.latest_seq())

    bus.subscribe(handler, name="probe")
    seq = await bus.publish(make_event(EventType.WAKE_UP, "atlas"))
    await bus.drain()
    assert seq == 1
    assert seen == [1]


async def test_type_filter(bus: EventBus) -> None:
    got: list[EventType] = []

    async def only_mail(e: Event) -> None:
        got.append(e.type)

    bus.subscribe(only_mail, types=[EventType.MAIL_TRIAGED], name="mail")
    await bus.publish(make_event(EventType.WAKE_UP, "atlas"))
    await bus.publish(make_event(EventType.MAIL_TRIAGED, "hermes"))
    await bus.drain()
    assert got == [EventType.MAIL_TRIAGED]


async def test_failing_handler_is_isolated(bus: EventBus) -> None:
    delivered: list[str] = []

    async def boom(_e: Event) -> None:
        raise RuntimeError("handler explosif")

    async def good(_e: Event) -> None:
        delivered.append("ok")

    bus.subscribe(boom, name="boom")
    bus.subscribe(good, name="good")
    seq = await bus.publish(make_event(EventType.SYSTEM_HEALTH, "sentinel"))
    await bus.drain()
    assert seq == 1  # publish n'a pas levé
    assert delivered == ["ok"]  # l'autre handler a bien reçu


async def test_unsubscribe(bus: EventBus) -> None:
    count = 0

    async def h(_e: Event) -> None:
        nonlocal count
        count += 1

    unsub = bus.subscribe(h, name="h")
    await bus.publish(make_event(EventType.WAKE_UP, "atlas"))
    await bus.drain()
    unsub()
    await bus.publish(make_event(EventType.WAKE_UP, "atlas"))
    await bus.drain()
    assert count == 1
