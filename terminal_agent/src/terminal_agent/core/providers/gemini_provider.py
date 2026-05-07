import os
from typing import Optional
from .base_provider import BaseLLMProvider, Message


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_KEY")
        self._model = None
        self._chat_session = None

    def _ensure_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel("gemini-2.0-flash")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete(self, prompt: str, **kwargs) -> str:
        self._ensure_model()
        response = self._model.generate_content(prompt)
        return response.text

    async def chat(self, messages: list[Message], **kwargs) -> str:
        self._ensure_model()
        if self._chat_session is None:
            self._chat_session = self._model.start_chat(history=[])
        last = messages[-1]
        response = self._chat_session.send_message(last.content)
        return response.text

    def reset_chat(self):
        self._chat_session = None
