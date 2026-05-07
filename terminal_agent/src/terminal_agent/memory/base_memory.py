"""Abstract memory interface for terminAI."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MemoryEntry:
    id: str
    role: str          # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class BaseMemory(ABC):
    """Every memory backend must implement this interface."""

    @abstractmethod
    async def save(self, role: str, content: str, metadata: Optional[dict] = None) -> str:
        """Persist a message; return its generated id."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Return the most relevant entries for *query*."""
        ...

    @abstractmethod
    async def get_recent(self, limit: int = 20) -> list[MemoryEntry]:
        """Return the most recent entries in chronological order."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Erase all stored memories."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources (DB connections, etc.)."""
        ...
