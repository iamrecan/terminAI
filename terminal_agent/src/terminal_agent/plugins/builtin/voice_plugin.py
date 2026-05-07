from __future__ import annotations

from typing import Callable
from ..base_plugin import BasePlugin


class VoicePlugin(BasePlugin):
    name = "voice"
    version = "0.1.0"
    description = "Voice recognition and text-to-speech"
    commands = ["listen", "speak", "stop", "conversation", "stop conversation"]

    def __init__(self):
        self._voice = None

    def setup(self) -> bool:
        # Voice commands are registered directly by TerminalAgent; no extra init needed.
        return True

    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        return {}  # All voice commands live in TerminalAgent._register_commands

    def on_unload(self):
        pass
