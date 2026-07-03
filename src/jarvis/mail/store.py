"""MailMemory — état local de HERMES v2 (projection SQLite).

Deux tables :
- `drafts` : brouillons de réponse générés par HERMES. **Jamais envoyés** (aucun canal
  d'envoi n'existe ; `MAIL_SEND` reste interdite). Simple persistance pour l'UI/relecture.
- `overrides` : règles de classification **apprises** — quand l'utilisateur corrige une
  catégorie dans l'UI, on mémorise `sender → category`. HERMES les consulte au prochain tri.

Même moule que `night/store.py` (connexion partagée + verrou). Aucune I/O externe.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS drafts (
    mail_id    TEXT PRIMARY KEY,
    sender     TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS overrides (
    sender     TEXT PRIMARY KEY,
    category   TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class Draft(BaseModel):
    mail_id: str
    sender: str
    subject: str
    body: str
    created_ts: str = ""


class MailMemory:
    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # --- Brouillons (jamais envoyés) --------------------------------------
    def save_draft(self, mail_id: str, sender: str, subject: str, body: str) -> Draft:
        draft = Draft(
            mail_id=mail_id, sender=sender, subject=subject, body=body, created_ts=_now_iso()
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO drafts (mail_id, sender, subject, body, created_ts) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(mail_id) DO UPDATE SET "
                "body=excluded.body, created_ts=excluded.created_ts",
                (draft.mail_id, draft.sender, draft.subject, draft.body, draft.created_ts),
            )
            self._conn.commit()
        return draft

    def get_draft(self, mail_id: str) -> Draft | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM drafts WHERE mail_id = ?", (mail_id,)
            ).fetchone()
        return self._row_to_draft(row) if row is not None else None

    def list_drafts(self) -> list[Draft]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM drafts ORDER BY created_ts DESC").fetchall()
        return [self._row_to_draft(r) for r in rows]

    # --- Règles apprises ---------------------------------------------------
    def set_override(self, sender: str, category: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO overrides (sender, category, updated_ts) VALUES (?, ?, ?) "
                "ON CONFLICT(sender) DO UPDATE SET category=excluded.category, "
                "updated_ts=excluded.updated_ts",
                (sender, category, _now_iso()),
            )
            self._conn.commit()

    def overrides(self) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute("SELECT sender, category FROM overrides").fetchall()
        return {r["sender"]: r["category"] for r in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_draft(row: sqlite3.Row) -> Draft:
        return Draft(
            mail_id=row["mail_id"],
            sender=row["sender"],
            subject=row["subject"],
            body=row["body"],
            created_ts=row["created_ts"],
        )
