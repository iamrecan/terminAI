"""Auto-detects and returns the best available calendar provider."""
import sys
from typing import Optional
from .base_calendar import BaseCalendarProvider


class CalendarProviderFactory:
    @staticmethod
    def get_available_provider() -> Optional[BaseCalendarProvider]:
        from ..calendars.apple_calendar import AppleCalendarProvider
        from ..calendars.google_calendar import GoogleCalendarProvider
        from ..calendars.caldav_calendar import CalDAVProvider
        from ...core.config import config

        preference = config.calendar_provider.lower()

        if preference == "apple":
            candidates: list[BaseCalendarProvider] = [AppleCalendarProvider()]
        elif preference == "google":
            candidates = [GoogleCalendarProvider()]
        elif preference == "caldav":
            candidates = [CalDAVProvider()]
        else:  # auto
            if sys.platform == "darwin":
                candidates = [AppleCalendarProvider(), GoogleCalendarProvider(), CalDAVProvider()]
            else:
                candidates = [GoogleCalendarProvider(), CalDAVProvider()]

        for provider in candidates:
            if provider.is_available():
                return provider

        return None
