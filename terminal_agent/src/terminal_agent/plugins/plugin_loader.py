"""Discovers and loads plugins via Python entry points (PEP 451)."""
from __future__ import annotations

import importlib.metadata
from .base_plugin import BasePlugin
from .plugin_registry import PluginRegistry


ENTRY_POINT_GROUP = "terminai.plugins"


class PluginLoader:
    @staticmethod
    def discover_and_load() -> list[str]:
        """Scan installed packages for terminai.plugins entry points and load them."""
        registry = PluginRegistry.instance()
        loaded: list[str] = []

        try:
            eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
        except Exception:
            return loaded

        for ep in eps:
            try:
                plugin_cls = ep.load()
                if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, BasePlugin)):
                    continue
                plugin = plugin_cls()
                if registry.register(plugin):
                    loaded.append(plugin.name)
            except Exception as e:
                print(f"Warning: failed to load plugin '{ep.name}': {e}")

        # Also load builtins
        loaded += PluginLoader._load_builtins()
        return loaded

    @staticmethod
    def _load_builtins() -> list[str]:
        from .builtin.notion_plugin import NotionPlugin
        from .builtin.voice_plugin import VoicePlugin
        from .builtin.calendar_plugin import CalendarPlugin
        from .builtin.coding_plugin import CodingPlugin

        registry = PluginRegistry.instance()
        loaded = []
        for plugin_cls in (NotionPlugin, VoicePlugin, CalendarPlugin, CodingPlugin):
            plugin = plugin_cls()
            # Only register if not already registered
            if registry.get(plugin.name) is None:
                if registry.register(plugin):
                    loaded.append(plugin.name)
        return loaded
