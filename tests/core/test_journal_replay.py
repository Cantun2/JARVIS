"""Le journal est la source de vérité : ordre total, filtres, rejouabilité."""

from __future__ import annotations

from jarvis.core.events import EventType, make_event
from jarvis.core.journal import SQLiteJournal


def test_append_returns_incrementing_seq(journal: SQLiteJournal) -> None:
    s1 = journal.append(make_event(EventType.WAKE_UP, "atlas"))
    s2 = journal.append(make_event(EventType.MAIL_RECEIVED, "hermes"))
    assert (s1, s2) == (1, 2)
    assert journal.latest_seq() == 2


def test_replay_preserves_order_and_payload(journal: SQLiteJournal) -> None:
    journal.append(make_event(EventType.WAKE_UP, "atlas", profile="deep-work"))
    journal.append(make_event(EventType.BRIEFING_READY, "oracle", text="Bonjour"))
    events = journal.replay()
    assert [e.type for e in events] == [EventType.WAKE_UP, EventType.BRIEFING_READY]
    assert events[0].payload["profile"] == "deep-work"
    assert events[1].source == "oracle"


def test_replay_since_seq_and_type_filter(journal: SQLiteJournal) -> None:
    journal.append(make_event(EventType.WAKE_UP, "atlas"))
    s2 = journal.append(make_event(EventType.MAIL_TRIAGED, "hermes"))
    journal.append(make_event(EventType.MAIL_TRIAGED, "hermes"))
    assert len(journal.replay(since_seq=s2)) == 1
    only_mail = journal.replay(types=[EventType.MAIL_TRIAGED])
    assert len(only_mail) == 2
    assert journal.replay(types=[]) == []


def test_agent_runs_lifecycle_view(journal: SQLiteJournal) -> None:
    journal.record_run_start("corr-1", "hermes")
    journal.record_run_end("corr-1", "finished", tokens=120, usd=0.01)
    status = journal.latest_status_by_agent()
    assert status["hermes"]["status"] == "finished"
    assert status["hermes"]["tokens"] == 120
    assert status["hermes"]["usd"] == 0.01


def test_latest_status_keeps_most_recent_run(journal: SQLiteJournal) -> None:
    journal.record_run_start("c1", "atlas")
    journal.record_run_end("c1", "failed", error="boom")
    journal.record_run_start("c2", "atlas")
    journal.record_run_end("c2", "finished")
    assert journal.latest_status_by_agent()["atlas"]["status"] == "finished"
