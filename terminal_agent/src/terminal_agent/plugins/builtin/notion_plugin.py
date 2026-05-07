from __future__ import annotations

from typing import Callable
from ..base_plugin import BasePlugin


class NotionPlugin(BasePlugin):
    name = "notion"
    version = "0.1.0"
    description = "Notion tasks and database integration"
    commands = ["tasks", "notion-search"]

    def __init__(self):
        self._notion = None

    def setup(self) -> bool:
        from ...core.config import config
        if not config.is_notion_enabled():
            return False
        try:
            from ...integrations.notion_integration import NotionIntegration
            self._notion = NotionIntegration()
            return True
        except Exception as e:
            print(f"Notion plugin setup failed: {e}")
            return False

    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        return {
            "tasks": (self._cmd_tasks, "Show today's tasks from Notion"),
            "notion-search": (self._cmd_search, "Search Notion database"),
        }

    def _cmd_tasks(self, *args):
        print(self._notion.get_tasks_for_today())

    def _cmd_search(self, *args):
        query = " ".join(args)
        if not query:
            print("Usage: notion-search <query>")
            return
        # Basic passthrough — extend when Notion search API is needed
        print(f"Searching Notion for: {query}")
        print(self._notion.get_tasks_for_today())
