"""Local SQLite-backed memory: conversations, messages, projects, notes.

No cloud storage of any kind. Everything lives in data/memory/memory.db,
resolved relative to PROJECT_ROOT so it stays portable on a USB drive.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from ..core import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    title TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'general',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ocr_text TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_id);
"""


class MemoryStore:
    def __init__(self, db_path: Path | None = None):
        paths.ensure_data_dirs()
        self.db_path = db_path or (paths.MEMORY_DIR / "memory.db")
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # --- projects -----------------------------------------------------
    def create_project(self, name: str) -> str:
        project_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
                (project_id, name, time.time()),
            )
        return project_id

    def list_projects(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    # --- conversations --------------------------------------------------
    def create_conversation(self, title: str, mode: str = "general", project_id: str | None = None) -> str:
        conv_id = str(uuid.uuid4())
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (id, project_id, title, mode, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conv_id, project_id, title, mode, now, now),
            )
        return conv_id

    def list_conversations(self, project_id: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE project_id = ? ORDER BY updated_at DESC",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def touch_conversation(self, conversation_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (time.time(), conversation_id),
            )

    # --- messages -------------------------------------------------------
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        ocr_text: str | None = None,
    ) -> str:
        msg_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, ocr_text, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, conversation_id, role, content, ocr_text, time.time()),
            )
        self.touch_conversation(conversation_id)
        return msg_id

    def get_history(self, conversation_id: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]

    # --- notes ------------------------------------------------------------
    def add_note(self, content: str, project_id: str | None = None) -> str:
        note_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO notes (id, project_id, content, created_at) VALUES (?, ?, ?, ?)",
                (note_id, project_id, content, time.time()),
            )
        return note_id

    def list_notes(self, project_id: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    # --- maintenance --------------------------------------------------------
    def clear_all(self) -> None:
        """Wipe all local memory. Irreversible; used by the UI's 'Clear memory' action."""
        with self._conn() as conn:
            conn.executescript(
                "DELETE FROM messages; DELETE FROM conversations; "
                "DELETE FROM notes; DELETE FROM projects;"
            )

    def clear_conversation(self, conversation_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def history_to_chat_messages(history: list[dict]) -> list[dict]:
    """Convert stored rows into OpenAI-style chat messages for the LLM."""
    out = []
    for row in history:
        content = row["content"]
        if row.get("ocr_text"):
            content = f"{content}\n\n[OCR-extracted text from attached image]:\n{row['ocr_text']}"
        out.append({"role": row["role"], "content": content})
    return out


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
