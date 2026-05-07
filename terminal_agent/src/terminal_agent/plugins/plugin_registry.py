from __future__ import annotations

from typing import Optional
from .base_plugin import BasePlugin


class PluginRegistry:
    """Singleton registry that holds all loaded plugins."""

    _instance: Optional["PluginRegistry"] = None

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}

    @classmethod
    def instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, plugin: BasePlugin) -> bool:
        """Load a plugin, call setup(), register its commands."""
        if not plugin.setup():
            return False
        self._plugins[plugin.name] = plugin
        plugin.on_load()
        return True

    def unregister(self, name: str) -> None:
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.on_unload()

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> list[BasePlugin]:
        return list(self._plugins.values())

    def enable(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = True
            print(f"Plugin '{name}' enabled.")
        else:
            print(f"Plugin '{name}' not found.")

    def disable(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.on_unload()
            plugin.enabled = False
            print(f"Plugin '{name}' disabled.")
        else:
            print(f"Plugin '{name}' not found.")

    def get_all_commands(self) -> dict[str, tuple]:
        """Collect commands from all enabled plugins."""
        cmds: dict[str, tuple] = {}
        for plugin in self._plugins.values():
            if plugin.enabled:
                cmds.update(plugin.get_commands())
        return cmds
