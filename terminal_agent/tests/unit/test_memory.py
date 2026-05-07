"""Unit tests for the memory module."""
import asyncio
from pathlib import Path

import pytest

from terminal_agent.memory import MemoryEntry, MemoryFactory
from terminal_agent.memory.sqlite_memory import SqliteMemory


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_memory.db"


@pytest.fixture
def mem(tmp_db):
    m = SqliteMemory(db_path=tmp_db)
    yield m
    asyncio.get_event_loop().run_until_complete(m.close())


@pytest.mark.asyncio
async def test_save_and_get_recent(tmp_db):
    m = SqliteMemory(db_path=tmp_db)
    await m.save("user", "hello world")
    await m.save("assistant", "hi there")
    entries = await m.get_recent(limit=10)
    assert len(entries) == 2
    assert entries[0].role == "user"
    assert entries[1].role == "assistant"
    await m.close()


@pytest.mark.asyncio
async def test_search_fts(tmp_db):
    m = SqliteMemory(db_path=tmp_db)
    await m.save("user", "I like Python programming")
    await m.save("user", "The weather is nice today")
    results = await m.search("Python", limit=5)
    assert len(results) >= 1
    assert "Python" in results[0].content
    await m.close()


@pytest.mark.asyncio
async def test_clear(tmp_db):
    m = SqliteMemory(db_path=tmp_db)
    await m.save("user", "test message")
    await m.clear()
    entries = await m.get_recent()
    assert entries == []
    await m.close()


@pytest.mark.asyncio
async def test_metadata(tmp_db):
    m = SqliteMemory(db_path=tmp_db)
    await m.save("user", "content", metadata={"session": "abc123", "lang": "en"})
    entries = await m.get_recent()
    assert entries[0].metadata["session"] == "abc123"
    await m.close()


def test_factory_returns_sqlite_by_default(tmp_db):
    mem = MemoryFactory.create(backend="sqlite", db_path=tmp_db)
    assert isinstance(mem, SqliteMemory)
    asyncio.get_event_loop().run_until_complete(mem.close())


def test_factory_auto_without_chroma(tmp_db, monkeypatch):
    """When chromadb is absent, auto should fall back to SQLite."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chromadb":
            raise ImportError("mocked absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mem = MemoryFactory.create(backend="auto", db_path=tmp_db)
    assert isinstance(mem, SqliteMemory)
    asyncio.get_event_loop().run_until_complete(mem.close())
