"""Central configuration — single source of truth for all settings.

All other modules import from here; they must NOT call load_dotenv() themselves.
Every field is Optional so the agent can start with partial credentials.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load once, at import time.  Explicit path keeps resolution deterministic.
_ENV_PATH = Path(__file__).parent.parent.parent.parent / "config" / ".env"
load_dotenv(_ENV_PATH)


@dataclass
class TerminalAIConfig:
    # LLM
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto"))
    offline_first: str = field(default_factory=lambda: os.getenv("OFFLINE_FIRST", "auto"))

    # Cloud LLM keys
    google_api_key: str | None = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_KEY"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    deepseek_api_key: str | None = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))

    # Local LLM
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"))

    # Notion
    notion_token: str | None = field(default_factory=lambda: os.getenv("NOTION_TOKEN"))
    notion_database_id: str | None = field(default_factory=lambda: os.getenv("NOTION_DATABASE_ID"))

    # Calendar
    calendar_provider: str = field(default_factory=lambda: os.getenv("CALENDAR_PROVIDER", "auto"))
    google_credentials_file: str = field(default_factory=lambda: os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))

    # Voice
    elevenlabs_api_key: str | None = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))
    default_language: str = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "en-US"))

    # Sprint 3 — Memory
    memory_enabled: bool = field(default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() == "true")
    memory_backend: str = field(default_factory=lambda: os.getenv("MEMORY_BACKEND", "auto"))
    memory_db_path: str | None = field(default_factory=lambda: os.getenv("MEMORY_DB_PATH"))

    # Sprint 4 placeholder
    proactive_enabled: bool = field(default_factory=lambda: os.getenv("PROACTIVE_ENABLED", "false").lower() == "true")

    # App
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Feature checks
    def is_notion_enabled(self) -> bool:
        return bool(self.notion_token and self.notion_database_id)

    def is_voice_enabled(self) -> bool:
        return True  # voice works with system TTS even without ElevenLabs

    def is_cloud_llm_available(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key or self.google_api_key)

    def available_llm_providers(self) -> list[str]:
        providers = []
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.openai_api_key:
            providers.append("openai")
        if self.google_api_key:
            providers.append("gemini")
        providers.append("ollama")  # always listed; availability checked at runtime
        return providers


# Module-level singleton — import this everywhere instead of constructing manually.
config = TerminalAIConfig()
