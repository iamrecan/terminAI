from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional


class BasePlugin(ABC):
    """Every plugin — builtin or community — must implement this interface."""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    commands: list[str] = []

    # Set by registry after loading
    enabled: bool = True

    @abstractmethod
    def setup(self) -> bool:
        """Called once when the plugin is loaded. Return False to abort loading."""
        ...

    @abstractmethod
    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        """Return {command_name: (handler_callable, description)}."""
        ...

    def on_load(self) -> None:
        """Optional lifecycle hook — called after commands are registered."""

    def on_unload(self) -> None:
        """Optional lifecycle hook — called before the plugin is disabled."""
