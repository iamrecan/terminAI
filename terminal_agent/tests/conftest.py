import pytest
import asyncio


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OFFLINE_FIRST", "false")
    monkeypatch.setenv("CALENDAR_PROVIDER", "none")
    monkeypatch.setenv("NOTION_TOKEN", "")
