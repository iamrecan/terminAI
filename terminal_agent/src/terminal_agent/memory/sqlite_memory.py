"""SQLite-backed memory — the default backend, zero extra deps."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base_memory import BaseMemory, MemoryEntry

_DDL = """
CREATE TABLE IF NOT EXISTS memories (
    id        TEXT PRIMARY KEY,
    role      TEXT NOT NULL,
    content   TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata  TEXT NOT NULL DEFAULT '{}'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
USING fts5(content, content=memories, content_rowid=rowid);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content)
    VALUES ('delete', old.rowid, old.content);
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;
"""


class SqliteMemory(BaseMemory):
    def __init__(self, db_path: Optional[Path] = None):
        self._path = db_path or (Path.home() / ".terminai" / "memory.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(_DDL)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata"]),
        )

    async def save(self, role: str, content: str, metadata: Optional[dict] = None) -> str:
        entry_id = str(uuid.uuid4())
        ts = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        async with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO memories (id, role, content, timestamp, metadata) VALUES (?,?,?,?,?)",
                (entry_id, role, content, ts, meta_json),
            )
            conn.commit()
        return entry_id

    async def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        async with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                """
                SELECT m.id, m.role, m.content, m.timestamp, m.metadata
                FROM memories_fts f
                JOIN memories m ON m.rowid = f.rowid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def get_recent(self, limit: int = 20) -> list[MemoryEntry]:
        async with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT id, role, content, timestamp, metadata FROM memories ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return list(reversed([self._row_to_entry(r) for r in rows]))

    async def clear(self) -> None:
        async with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM memories_fts")
            conn.commit()

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    @property
    def db_path(self) -> Path:
        return self._path
