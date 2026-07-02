"""Source de mails : abstraction + backends Mock (défaut) et Gmail (réel).

Même moule que `io/telegram.py` : Protocol + Mock + Stub réel derrière config + factory.
Le backend Gmail importe les libs Google en paresseux (extra `[google]`) et accepte un
service injectable → testable hors-ligne, sans jamais toucher le réseau.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from jarvis.config import Settings
from jarvis.logging import get_logger

log = get_logger("jarvis.mail")


class Mail(BaseModel):
    """Un email normalisé, indépendant de la source."""

    id: str
    sender: str
    subject: str
    body: str


@runtime_checkable
class MailSource(Protocol):
    async def fetch(self, *, limit: int = 50) -> list[Mail]: ...


class MockMailSource:
    """Renvoie les mails factices (défaut, hors-ligne, déterministe)."""

    def __init__(self, mails: tuple[Mail, ...] | None = None) -> None:
        self._mails = mails

    async def fetch(self, *, limit: int = 50) -> list[Mail]:
        if self._mails is None:
            # Import paresseux : évite un cycle io.mail ↔ fixtures au chargement.
            from jarvis.agents.mocks.mail_fixtures import MOCK_MAILS

            self._mails = MOCK_MAILS
        return list(self._mails[:limit])


def _header(headers: list[dict[str, str]], name: str) -> str:
    lname = name.lower()
    for h in headers:
        if h.get("name", "").lower() == lname:
            return h.get("value", "")
    return ""


def _decode_b64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


def _extract_body(payload: dict[str, Any]) -> str:
    """Extrait le texte d'un message Gmail (parcourt les parts, priorité text/plain)."""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    if mime == "text/plain" and body.get("data"):
        return _decode_b64url(body["data"])
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    if body.get("data"):  # repli : n'importe quel corps encodé
        return _decode_b64url(body["data"])
    return ""


def parse_gmail_message(msg: dict[str, Any]) -> Mail:
    """Transforme un message Gmail (format=full) en `Mail`."""
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    body = _extract_body(payload) or msg.get("snippet", "")
    return Mail(
        id=str(msg.get("id", "")),
        sender=_header(headers, "From"),
        subject=_header(headers, "Subject"),
        body=body,
    )


class GmailMailSource:
    """Récupère les mails via l'API Gmail. Service injectable pour les tests."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
        *,
        service: Any | None = None,
        query: str = "in:inbox",
    ) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = service
        self._query = query

    def _build_service(self) -> Any:
        # Import paresseux : l'extra [google] n'est pas requis en mode mock.
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not self._token_path:
            raise RuntimeError("GMAIL_TOKEN_PATH manquant (cf. docs/MANUAL_SETUP.md)")
        creds = Credentials.from_authorized_user_file(
            self._token_path, ["https://www.googleapis.com/auth/gmail.readonly"]
        )
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    async def fetch(self, *, limit: int = 50) -> list[Mail]:
        service = self._service or self._build_service()
        return await asyncio.to_thread(self._fetch_sync, service, limit)

    def _fetch_sync(self, service: Any, limit: int) -> list[Mail]:
        listing = (
            service.users().messages().list(userId="me", q=self._query, maxResults=limit).execute()
        )
        mails: list[Mail] = []
        for ref in listing.get("messages", [])[:limit]:
            full = (
                service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            )
            mails.append(parse_gmail_message(full))
        return mails


def build_mail(settings: Settings) -> MailSource:
    if settings.mode == "real" and settings.mail_backend == "gmail":
        log.info("mail_backend", backend="gmail")
        return GmailMailSource(settings.gmail_credentials_path, settings.gmail_token_path)
    return MockMailSource()
