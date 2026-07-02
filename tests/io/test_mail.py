"""MailSource : mock par défaut, parsing Gmail hors-ligne, factory."""

from __future__ import annotations

import base64
from typing import Any

from jarvis.config import Settings
from jarvis.io.mail import (
    GmailMailSource,
    Mail,
    MailSource,
    MockMailSource,
    build_mail,
    parse_gmail_message,
)


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _gmail_message(msg_id: str, sender: str, subject: str, body: str) -> dict[str, Any]:
    return {
        "id": msg_id,
        "snippet": "snippet",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": subject},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": _b64url(body)}}],
        },
    }


class _FakeExec:
    def __init__(self, result: Any) -> None:
        self._result = result

    def execute(self) -> Any:
        return self._result


class _FakeMessages:
    def __init__(self, listing: Any, messages: dict[str, Any]) -> None:
        self._listing = listing
        self._messages = messages

    def list(self, **_kw: Any) -> _FakeExec:
        return _FakeExec(self._listing)

    def get(self, *, userId: str, id: str, format: str) -> _FakeExec:
        return _FakeExec(self._messages[id])


class _FakeUsers:
    def __init__(self, messages: _FakeMessages) -> None:
        self._messages = messages

    def messages(self) -> _FakeMessages:
        return self._messages


class _FakeService:
    def __init__(self, listing: Any, messages: dict[str, Any]) -> None:
        self._users = _FakeUsers(_FakeMessages(listing, messages))

    def users(self) -> _FakeUsers:
        return self._users


def test_mock_source_is_default_and_matches_protocol() -> None:
    source = build_mail(Settings(mode="mock"))
    assert isinstance(source, MockMailSource)
    assert isinstance(source, MailSource)


async def test_mock_source_respects_limit() -> None:
    mails = await MockMailSource().fetch(limit=3)
    assert len(mails) == 3
    assert all(isinstance(m, Mail) for m in mails)


def test_parse_gmail_message_extracts_fields() -> None:
    msg = _gmail_message("m1", "alice@example.com", "Sujet test", "Corps du message")
    mail = parse_gmail_message(msg)
    assert mail.id == "m1"
    assert mail.sender == "alice@example.com"
    assert mail.subject == "Sujet test"
    assert mail.body == "Corps du message"


async def test_gmail_source_fetches_via_injected_service() -> None:
    listing = {"messages": [{"id": "m1"}, {"id": "m2"}]}
    messages = {
        "m1": _gmail_message("m1", "a@x.com", "Un", "corps un"),
        "m2": _gmail_message("m2", "b@x.com", "Deux", "corps deux"),
    }
    source = GmailMailSource(service=_FakeService(listing, messages))
    assert isinstance(source, MailSource)
    mails = await source.fetch(limit=10)
    assert [m.subject for m in mails] == ["Un", "Deux"]
    assert mails[0].body == "corps un"


def test_build_mail_gmail_when_real_and_configured() -> None:
    source = build_mail(Settings(mode="real", mail_backend="gmail", gmail_token_path="tok.json"))
    assert isinstance(source, GmailMailSource)
