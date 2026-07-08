"""ConversationStore — mémoire multi-tours des dialogues (projection SQLite).

Deux tables :
- `conversations` : un fil par (agent, session). `agent` = interlocuteur.
- `messages`      : les tours (system/user/assistant), ordonnés chronologiquement.

Même moule que `mail/store.py` (connexion partagée + verrou, WAL, modèles frozen).
Service d'état **non gaté** par permission (comme `tasks`/`mail_memory`).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from jarvis.chat.models import ChatRole, Conversation, ConvMessage
from jarvis.core.events import uuid7

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    agent      TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    created_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    tokens          INTEGER NOT NULL DEFAULT 0,
    created_ts      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_messages_conv ON messages(conversation_id);
"""


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class ConversationStore:
    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def create(self, agent: str, title: str = "") -> Conversation:
        conv = Conversation(
            id=uuid7(), agent=agent, title=title, created_ts=_now_iso(), updated_ts=_now_iso()
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO conversations (id, agent, title, created_ts, updated_ts) "
                "VALUES (?, ?, ?, ?, ?)",
                (conv.id, conv.agent, conv.title, conv.created_ts, conv.updated_ts),
            )
            self._conn.commit()
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return self._row_to_conv(row) if row is not None else None

    def list_conversations(self, agent: str | None = None) -> list[Conversation]:
        with self._lock:
            if agent is None:
                rows = self._conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_ts DESC"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM conversations WHERE agent = ? ORDER BY updated_ts DESC",
                    (agent,),
                ).fetchall()
        return [self._row_to_conv(r) for r in rows]

    def append(
        self, conversation_id: str, role: ChatRole, content: str, *, tokens: int = 0
    ) -> ConvMessage:
        msg = ConvMessage(
            id=uuid7(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens=tokens,
            created_ts=_now_iso(),
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, tokens, created_ts) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (msg.id, msg.conversation_id, msg.role, msg.content, msg.tokens, msg.created_ts),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_ts = ? WHERE id = ?",
                (msg.created_ts, conversation_id),
            )
            self._conn.commit()
        return msg

    def history(self, conversation_id: str, *, limit: int = 20) -> list[ConvMessage]:
        """Les `limit` derniers messages, du plus ancien au plus récent (borne le prompt)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? "
                "ORDER BY created_ts DESC, rowid DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [self._row_to_msg(r) for r in reversed(rows)]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_conv(row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            agent=row["agent"],
            title=row["title"],
            created_ts=row["created_ts"],
            updated_ts=row["updated_ts"],
        )

    @staticmethod
    def _row_to_msg(row: sqlite3.Row) -> ConvMessage:
        return ConvMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            tokens=row["tokens"],
            created_ts=row["created_ts"],
        )
