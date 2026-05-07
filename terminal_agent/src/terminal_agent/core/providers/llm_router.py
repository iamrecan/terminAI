"""
Hybrid LLM Router.

Task routing:
  quick_answer / event_parsing / summarization  → local-fast (OLLAMA_MODEL_FAST)
  deep_reasoning / code_generation              → local-deep (OLLAMA_MODEL_DEEP) or cloud

env vars:
  OLLAMA_MODEL_FAST  — default gemma3:4b   (hızlı, sesli komutlar için)
  OLLAMA_MODEL_DEEP  — default qwen3:8b    (derin reasoning, kod için)
  OFFLINE_FIRST=true/false/auto
"""
import os
from typing import Optional
from .base_provider import BaseLLMProvider, Message
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


_TASK_ROUTING: dict[str, str] = {
    "quick_answer":    "local_fast",
    "event_parsing":   "local_fast",
    "summarization":   "local_fast",
    "deep_reasoning":  "local_deep",
    "code_generation": "local_deep",
}


class LLMRouter:
    def __init__(self):
        fast_model = os.getenv("OLLAMA_MODEL_FAST", "gemma3:4b")
        deep_model = os.getenv("OLLAMA_MODEL_DEEP", os.getenv("OLLAMA_MODEL", "qwen3:8b"))

        self._fast_provider = OllamaProvider(model=fast_model)
        self._deep_provider = OllamaProvider(model=deep_model)
        # If both point to same model, reuse instance
        if fast_model == deep_model:
            self._deep_provider = self._fast_provider

        self._local_providers: list[BaseLLMProvider] = [self._fast_provider, self._deep_provider]
        self._cloud_providers: list[BaseLLMProvider] = [
            p for p in [AnthropicProvider(), OpenAIProvider(), GeminiProvider()]
            if p.is_available
        ]
        offline_env = os.getenv("OFFLINE_FIRST", "auto").lower()
        self._offline_first: Optional[bool] = (
            True if offline_env == "true"
            else False if offline_env == "false"
            else None  # None == auto
        )

    @property
    def available_providers(self) -> list[BaseLLMProvider]:
        result = []
        if self._offline_first is True:
            result = [p for p in self._local_providers if p.is_available]
            result += [p for p in self._cloud_providers if p.is_available]
        elif self._offline_first is False:
            result = [p for p in self._cloud_providers if p.is_available]
            result += [p for p in self._local_providers if p.is_available]
        else:
            result = [p for p in self._local_providers + self._cloud_providers if p.is_available]
        return result

    def _select(self, task_type: str) -> BaseLLMProvider:
        if self._offline_first is True:
            ordered = (
                [p for p in self._local_providers if p.is_available]
                + [p for p in self._cloud_providers if p.is_available]
            )
        elif self._offline_first is False:
            ordered = (
                [p for p in self._cloud_providers if p.is_available]
                + [p for p in self._local_providers if p.is_available]
            )
        else:
            preferred = _TASK_ROUTING.get(task_type, "local_deep")
            if preferred == "local_fast":
                # fast model first, then deep, then cloud
                ordered = (
                    ([self._fast_provider] if self._fast_provider.is_available else [])
                    + ([self._deep_provider] if self._deep_provider.is_available and self._deep_provider is not self._fast_provider else [])
                    + [p for p in self._cloud_providers if p.is_available]
                )
            else:
                # deep model first, then fast, then cloud
                ordered = (
                    ([self._deep_provider] if self._deep_provider.is_available else [])
                    + ([self._fast_provider] if self._fast_provider.is_available and self._fast_provider is not self._deep_provider else [])
                    + [p for p in self._cloud_providers if p.is_available]
                )

        if not ordered:
            raise RuntimeError(
                "No LLM provider available. Set an API key (ANTHROPIC_API_KEY, "
                "OPENAI_API_KEY, GOOGLE_API_KEY) or start Ollama."
            )
        return ordered[0]

    async def complete(self, prompt: str, task_type: str = "quick_answer", **kwargs) -> str:
        provider = self._select(task_type)
        return await provider.complete(prompt, **kwargs)

    async def chat(self, messages: list[Message], task_type: str = "deep_reasoning", **kwargs) -> str:
        provider = self._select(task_type)
        return await provider.chat(messages, **kwargs)

    def status(self) -> dict[str, bool]:
        result: dict[str, bool] = {}
        result[f"ollama/{self._fast_provider._model} (fast)"] = self._fast_provider.is_available
        if self._deep_provider is not self._fast_provider:
            result[f"ollama/{self._deep_provider._model} (deep)"] = self._deep_provider.is_available
        for p in self._cloud_providers:
            result[p.name] = p.is_available
        return result
