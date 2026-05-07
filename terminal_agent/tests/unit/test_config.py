"""Unit tests for config module."""
import pytest


class TestTerminalAIConfig:
    def test_notion_disabled_without_credentials(self, monkeypatch):
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        from src.terminal_agent.core.config import TerminalAIConfig
        cfg = TerminalAIConfig()
        assert not cfg.is_notion_enabled()

    def test_notion_enabled_with_credentials(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "secret_token")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db-id")
        from src.terminal_agent.core.config import TerminalAIConfig
        cfg = TerminalAIConfig()
        assert cfg.is_notion_enabled()

    def test_available_providers_list(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_AI_KEY", raising=False)
        from src.terminal_agent.core.config import TerminalAIConfig
        cfg = TerminalAIConfig()
        providers = cfg.available_llm_providers()
        assert "anthropic" in providers
        assert "openai" not in providers
        assert "ollama" in providers  # always listed

    def test_debug_default_false(self):
        from src.terminal_agent.core.config import TerminalAIConfig
        cfg = TerminalAIConfig()
        assert cfg.debug is False
