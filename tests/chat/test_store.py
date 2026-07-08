"""ConversationStore : création, ajout, historique borné, isolation par conversation."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.chat.store import ConversationStore


@pytest.fixture
def store() -> Iterator[ConversationStore]:
    s = ConversationStore(":memory:")
    yield s
    s.close()


def test_create_and_get(store: ConversationStore) -> None:
    conv = store.create("JARVIS", title="Bonjour")
    assert conv.agent == "JARVIS"
    fetched = store.get(conv.id)
    assert fetched is not None and fetched.id == conv.id


def test_append_and_history_ordering(store: ConversationStore) -> None:
    conv = store.create("JARVIS")
    store.append(conv.id, "user", "salut")
    store.append(conv.id, "assistant", "bonjour")
    store.append(conv.id, "user", "ça va ?")
    hist = store.history(conv.id)
    assert [m.role for m in hist] == ["user", "assistant", "user"]
    assert [m.content for m in hist] == ["salut", "bonjour", "ça va ?"]


def test_history_limit_keeps_most_recent(store: ConversationStore) -> None:
    conv = store.create("JARVIS")
    for i in range(30):
        store.append(conv.id, "user", f"msg{i}")
    hist = store.history(conv.id, limit=5)
    assert len(hist) == 5
    assert [m.content for m in hist] == [f"msg{i}" for i in range(25, 30)]


def test_conversations_are_isolated(store: ConversationStore) -> None:
    a = store.create("JARVIS")
    b = store.create("NEMESIS")
    store.append(a.id, "user", "dans A")
    store.append(b.id, "user", "dans B")
    assert [m.content for m in store.history(a.id)] == ["dans A"]
    assert [m.content for m in store.history(b.id)] == ["dans B"]


def test_list_filters_by_agent(store: ConversationStore) -> None:
    store.create("JARVIS")
    store.create("NEMESIS")
    store.create("JARVIS")
    assert len(store.list_conversations()) == 3
    assert len(store.list_conversations("JARVIS")) == 2
    assert len(store.list_conversations("NEMESIS")) == 1
