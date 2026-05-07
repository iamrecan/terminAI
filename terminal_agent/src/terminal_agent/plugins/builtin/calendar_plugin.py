from __future__ import annotations

from typing import Callable
from ..base_plugin import BasePlugin


class CalendarPlugin(BasePlugin):
    name = "calendar"
    version = "0.1.0"
    description = "Calendar events and reminders"
    commands = ["events", "agenda", "create-event"]

    def __init__(self):
        self._calendar = None

    def setup(self) -> bool:
        from ...integrations.calendars import CalendarProviderFactory
        self._calendar = CalendarProviderFactory.get_available_provider()
        return self._calendar is not None

    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        if not self._calendar:
            return {}
        return {
            "cal-events": (self._cmd_events, f"Show today's events ({self._calendar.name})"),
            "cal-week": (self._cmd_week, "Show events for the next 7 days"),
        }

    def _cmd_events(self, *args):
        events = self._calendar.get_today_events()
        if not events:
            print("No events today.")
            return
        for ev in events:
            print(f"  {ev.start.strftime('%H:%M')} — {ev.title}")

    def _cmd_week(self, *args):
        events = self._calendar.get_events(days_ahead=7)
        if not events:
            print("No events in the next 7 days.")
            return
        for ev in events:
            print(f"  {ev.start.strftime('%a %d %b %H:%M')} — {ev.title}")
