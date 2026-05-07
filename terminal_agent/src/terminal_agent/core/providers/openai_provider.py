import os
from typing import Optional
from .base_provider import BaseLLMProvider, Message


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.chat([Message(role="user", content=prompt)], **kwargs)

    async def chat(self, messages: list[Message], **kwargs) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key)
        response = await client.chat.completions.create(
            model=kwargs.get("model", self._model),
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return response.choices[0].message.content
