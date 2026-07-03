"""MailMemory : brouillons (jamais envoyés) + règles de classification apprises."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.mail.store import MailMemory


@pytest.fixture
def mem() -> Iterator[MailMemory]:
    m = MailMemory(":memory:")
    yield m
    m.close()


def test_save_and_get_draft(mem: MailMemory) -> None:
    assert mem.get_draft("m1") is None
    draft = mem.save_draft("m1", "a@x.com", "Sujet", "Bonjour,\n…")
    assert draft.created_ts
    got = mem.get_draft("m1")
    assert got is not None and got.body.startswith("Bonjour")


def test_save_draft_upserts(mem: MailMemory) -> None:
    mem.save_draft("m1", "a@x.com", "Sujet", "v1")
    mem.save_draft("m1", "a@x.com", "Sujet", "v2")
    got = mem.get_draft("m1")
    assert got is not None and got.body == "v2"
    assert len(mem.list_drafts()) == 1


def test_overrides_roundtrip_and_upsert(mem: MailMemory) -> None:
    assert mem.overrides() == {}
    mem.set_override("news@x.com", "urgent")
    mem.set_override("boss@x.com", "action")
    mem.set_override("news@x.com", "spam")  # écrase
    assert mem.overrides() == {"news@x.com": "spam", "boss@x.com": "action"}
