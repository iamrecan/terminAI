import os
import subprocess
import aiohttp
import json
from typing import Optional
from .base_provider import BaseLLMProvider, Message


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self._base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        if self._available is None:
            try:
                result = subprocess.run(
                    ["ollama", "list"], capture_output=True, text=True, timeout=3
                )
                self._available = result.returncode == 0
            except Exception:
                self._available = False
        return self._available

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.chat([Message(role="user", content=prompt)], **kwargs)

    async def chat(self, messages: list[Message], **kwargs) -> str:
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._base_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=180)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("message", {}).get("content", "")
                    text = await resp.text()
                    raise RuntimeError(f"Ollama error {resp.status}: {text}")
        except aiohttp.ClientConnectorError:
            raise RuntimeError("Ollama is not running. Start it with: ollama serve")
