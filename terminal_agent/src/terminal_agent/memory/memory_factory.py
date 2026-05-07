"""Factory that picks the right memory backend at runtime."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .base_memory import BaseMemory


def _chromadb_available() -> bool:
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


class MemoryFactory:
    @staticmethod
    def create(
        backend: Optional[str] = None,
        db_path: Optional[Path] = None,
    ) -> BaseMemory:
        """
        backend: "sqlite" | "chroma" | "auto" | None
          auto / None → chroma if installed, else sqlite
        """
        chosen = (backend or os.getenv("MEMORY_BACKEND", "auto")).lower()

        if chosen == "chroma":
            from .chroma_memory import ChromaMemory
            return ChromaMemory(db_path=db_path)

        if chosen == "auto" and _chromadb_available():
            from .chroma_memory import ChromaMemory
            return ChromaMemory(db_path=db_path)

        from .sqlite_memory import SqliteMemory
        return SqliteMemory(db_path=db_path)
