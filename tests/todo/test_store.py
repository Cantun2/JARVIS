"""TodoStore : CRUD, due_reminders (bornes + dédup), appointments_on, range mensuel."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jarvis.todo.models import TodoDraft, TodoKind, TodoStatus
from jarvis.todo.store import TodoStore


@pytest.fixture
def store() -> Iterator[TodoStore]:
    s = TodoStore(":memory:")
    yield s
    s.close()


def test_add_get_and_list_by_date(store: TodoStore) -> None:
    t = store.add(TodoDraft(title="Écrire script", date="2026-07-08"))
    assert store.get(t.id) is not None
    assert [x.title for x in store.list_by_date("2026-07-08")] == ["Écrire script"]
    assert store.list_by_date("2026-07-09") == []


def test_update_and_status_and_delete(store: TodoStore) -> None:
    t = store.add(TodoDraft(title="A", date="2026-07-08"))
    store.update(t.id, title="B", tags=["mail"])
    updated = store.get(t.id)
    assert updated is not None and updated.title == "B" and updated.tags == ("mail",)
    store.set_status(t.id, TodoStatus.DONE)
    assert store.get(t.id).status == TodoStatus.DONE  # type: ignore[union-attr]
    store.delete(t.id)
    assert store.get(t.id) is None


def test_update_unknown_raises(store: TodoStore) -> None:
    with pytest.raises(KeyError):
        store.update("nope", title="x")


def test_update_rejects_unknown_field(store: TodoStore) -> None:
    t = store.add(TodoDraft(title="A", date="2026-07-08"))
    with pytest.raises(ValueError, match="non modifiables"):
        store.update(t.id, reminded_ts="hack")


def test_appointments_on_filters_kind_and_status(store: TodoStore) -> None:
    store.add(
        TodoDraft(
            title="RDV dentiste", date="2026-07-08", kind=TodoKind.APPOINTMENT, time="10:00"
        )
    )
    store.add(TodoDraft(title="Tâche simple", date="2026-07-08"))
    appts = store.appointments_on("2026-07-08")
    assert [a.title for a in appts] == ["RDV dentiste"]


def test_due_reminders_boundary_and_dedup(store: TodoStore) -> None:
    # RDV à 10:00, rappel 15 min avant → échéance de rappel 09:45.
    t = store.add(
        TodoDraft(
            title="Appeler client",
            date="2026-07-08",
            kind=TodoKind.APPOINTMENT,
            time="10:00",
            remind_lead_min=15,
        )
    )
    # Avant 09:45 → pas encore dû.
    assert store.due_reminders("2026-07-08T09:30:00") == []
    # Après 09:45 → dû.
    due = store.due_reminders("2026-07-08T09:50:00")
    assert [d.id for d in due] == [t.id]
    # Une fois marqué rappelé → plus jamais (dédup).
    store.mark_reminded(t.id)
    assert store.due_reminders("2026-07-08T12:00:00") == []


def test_due_reminders_untimed_uses_default_hour(store: TodoStore) -> None:
    t = store.add(TodoDraft(title="Tâche du jour", date="2026-07-08"))  # sans heure
    # default_hour=9 → rappel à 09:00.
    assert store.due_reminders("2026-07-08T08:00:00", default_hour=9) == []
    assert [d.id for d in store.due_reminders("2026-07-08T09:30:00", default_hour=9)] == [t.id]


def test_done_tasks_are_not_reminded(store: TodoStore) -> None:
    t = store.add(TodoDraft(title="Fait", date="2026-07-08", time="08:00"))
    store.set_status(t.id, TodoStatus.DONE)
    assert store.due_reminders("2026-07-08T12:00:00") == []


def test_list_range_spans_month(store: TodoStore) -> None:
    store.add(TodoDraft(title="1er", date="2026-07-01"))
    store.add(TodoDraft(title="15", date="2026-07-15"))
    store.add(TodoDraft(title="aout", date="2026-08-02"))
    got = store.list_range("2026-07-01", "2026-07-31")
    assert {t.title for t in got} == {"1er", "15"}
