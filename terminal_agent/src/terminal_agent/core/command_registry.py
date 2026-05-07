from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Command:
    name: str
    handler: Callable
    description: str
    category: str
    aliases: list[str] = field(default_factory=list)


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        category: str,
        aliases: Optional[list[str]] = None,
    ) -> None:
        cmd = Command(name=name, handler=handler, description=description,
                      category=category, aliases=aliases or [])
        self._commands[name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

    def dispatch(self, name: str, args: list[str]) -> Any:
        cmd = self._commands.get(name)
        if cmd is None:
            return None
        return cmd.handler(*args)

    def has(self, name: str) -> bool:
        return name in self._commands

    def list_commands(self, category: Optional[str] = None) -> list[Command]:
        seen: set[str] = set()
        result: list[Command] = []
        for cmd in self._commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            if category is None or cmd.category == category:
                result.append(cmd)
        return sorted(result, key=lambda c: (c.category, c.name))

    def categories(self) -> list[str]:
        return sorted({cmd.category for cmd in self._commands.values()})
