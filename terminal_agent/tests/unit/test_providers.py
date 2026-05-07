"""Unit tests for LLM providers — all external calls are mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOllamaProvider:
    def test_name(self):
        from src.terminal_agent.core.providers.ollama_provider import OllamaProvider
        assert OllamaProvider().name == "ollama"

    def test_unavailable_when_ollama_not_installed(self):
        from src.terminal_agent.core.providers.ollama_provider import OllamaProvider
        p = OllamaProvider()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert not p.is_available

    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        from src.terminal_agent.core.providers.ollama_provider import OllamaProvider
        from src.terminal_agent.core.providers.base_provider import Message
        p = OllamaProvider()
        mock_response = {"message": {"content": "Hello!"}}
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(
                    post=MagicMock(return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=mock_resp),
                        __aexit__=AsyncMock(return_value=False),
                    ))
                )
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await p.chat([Message(role="user", content="hi")])
            assert result == "Hello!"


class TestGeminiProvider:
    def test_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_AI_KEY", raising=False)
        from src.terminal_agent.core.providers.gemini_provider import GeminiProvider
        p = GeminiProvider(api_key=None)
        assert not p.is_available

    def test_available_with_key(self):
        from src.terminal_agent.core.providers.gemini_provider import GeminiProvider
        p = GeminiProvider(api_key="fake-key")
        assert p.is_available


class TestOpenAIProvider:
    def test_name(self):
        from src.terminal_agent.core.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider().name == "openai"

    def test_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from src.terminal_agent.core.providers.openai_provider import OpenAIProvider
        assert not OpenAIProvider().is_available


class TestAnthropicProvider:
    def test_name(self):
        from src.terminal_agent.core.providers.anthropic_provider import AnthropicProvider
        assert AnthropicProvider().name == "anthropic"

    def test_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from src.terminal_agent.core.providers.anthropic_provider import AnthropicProvider
        assert not AnthropicProvider().is_available


class TestLLMRouter:
    def test_raises_when_no_provider(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_AI_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from src.terminal_agent.core.providers.llm_router import LLMRouter
        from src.terminal_agent.core.providers.ollama_provider import OllamaProvider
        with patch.object(OllamaProvider, "is_available", new_callable=lambda: property(lambda self: False)):
            router = LLMRouter()
            with pytest.raises(RuntimeError, match="No LLM provider"):
                router._select("quick_answer")

    def test_status_returns_dict(self):
        from src.terminal_agent.core.providers.llm_router import LLMRouter
        router = LLMRouter()
        status = router.status()
        assert isinstance(status, dict)
        assert any("ollama" in key for key in status)
