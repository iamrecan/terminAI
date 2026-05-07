import os
from typing import Optional
from .base_provider import BaseLLMProvider, Message


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.chat([Message(role="user", content=prompt)], **kwargs)

    async def chat(self, messages: list[Message], **kwargs) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        system_messages = [m.content for m in messages if m.role == "system"]
        user_messages = [
            {"role": m.role, "content": m.content}
            for m in messages if m.role != "system"
        ]

        kwargs_send = dict(
            model=kwargs.get("model", self._model),
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=user_messages,
        )
        if system_messages:
            kwargs_send["system"] = system_messages[0]

        response = await client.messages.create(**kwargs_send)
        return response.content[0].text
