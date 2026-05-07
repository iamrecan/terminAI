"""ChromaDB-backed memory — semantic search via vector embeddings.

Install: pip install terminai[memory]
Falls back transparently to SqliteMemory if chromadb is not installed.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base_memory import BaseMemory, MemoryEntry
from .sqlite_memory import SqliteMemory


class ChromaMemory(BaseMemory):
    """Semantic memory using ChromaDB for similarity search.

    Inherits SQLite for get_recent / storage; overrides search() with vectors.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._sqlite = SqliteMemory(db_path=db_path)
        chroma_dir = (db_path or (Path.home() / ".terminai" / "memory.db")).parent / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        import chromadb  # noqa: PLC0415 — intentional late import
        self._client = chromadb.PersistentClient(path=str(chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name="terminai_memory",
            metadata={"hnsw:space": "cosine"},
        )

    async def save(self, role: str, content: str, metadata: Optional[dict] = None) -> str:
        entry_id = await self._sqlite.save(role, content, metadata)
        meta = metadata or {}
        meta["role"] = role
        meta["timestamp"] = datetime.now().isoformat()
        self._collection.upsert(
            ids=[entry_id],
            documents=[content],
            metadatas=[{k: str(v) for k, v in meta.items()}],
        )
        return entry_id

    async def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        results = self._collection.query(
            query_texts=[query],
            n_results=min(limit, self._collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        entries: list[MemoryEntry] = []
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            entries.append(
                MemoryEntry(
                    id=doc_id,
                    role=meta.get("role", "unknown"),
                    content=results["documents"][0][i],
                    timestamp=datetime.fromisoformat(
                        meta.get("timestamp", datetime.now().isoformat())
                    ),
                    metadata={k: v for k, v in meta.items() if k not in ("role", "timestamp")},
                )
            )
        return entries

    async def get_recent(self, limit: int = 20) -> list[MemoryEntry]:
        return await self._sqlite.get_recent(limit)

    async def clear(self) -> None:
        await self._sqlite.clear()
        self._collection.delete(where={"role": {"$ne": "__nonexistent__"}})

    async def close(self) -> None:
        await self._sqlite.close()
