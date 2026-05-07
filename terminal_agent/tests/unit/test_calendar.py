"""Unit tests for calendar providers."""
import sys
import pytest
import datetime


class TestCalendarEvent:
    def test_defaults(self):
        from src.terminal_agent.integrations.calendars.base_calendar import CalendarEvent
        now = datetime.datetime.now()
        ev = CalendarEvent(title="Test", start=now, end=now)
        assert ev.location == ""
        assert ev.event_type == "event"
        assert not ev.completed


class TestCalendarFactory:
    def test_returns_apple_on_macos(self):
        if sys.platform != "darwin":
            pytest.skip("macOS only")
        from src.terminal_agent.integrations.calendars.calendar_factory import CalendarProviderFactory
        from src.terminal_agent.integrations.calendars.apple_calendar import AppleCalendarProvider
        from unittest.mock import patch
        with patch.object(AppleCalendarProvider, "is_available", return_value=True):
            provider = CalendarProviderFactory.get_available_provider()
            assert provider is not None

    def test_returns_none_when_nothing_available(self, monkeypatch):
        from src.terminal_agent.integrations.calendars import CalendarProviderFactory
        from src.terminal_agent.integrations.calendars.apple_calendar import AppleCalendarProvider
        from src.terminal_agent.integrations.calendars.google_calendar import GoogleCalendarProvider
        from src.terminal_agent.integrations.calendars.caldav_calendar import CalDAVProvider
        from unittest.mock import patch
        monkeypatch.setenv("CALENDAR_PROVIDER", "auto")
        with patch.object(AppleCalendarProvider, "is_available", return_value=False), \
             patch.object(GoogleCalendarProvider, "is_available", return_value=False), \
             patch.object(CalDAVProvider, "is_available", return_value=False):
            provider = CalendarProviderFactory.get_available_provider()
            assert provider is None


class TestGoogleCalendarProvider:
    def test_unavailable_without_credentials(self, tmp_path):
        from src.terminal_agent.integrations.calendars.google_calendar import GoogleCalendarProvider
        p = GoogleCalendarProvider(credentials_file=str(tmp_path / "creds.json"))
        assert not p.is_available()


class TestCalDAVProvider:
    def test_unavailable_without_env(self, monkeypatch):
        monkeypatch.delenv("CALDAV_URL", raising=False)
        from src.terminal_agent.integrations.calendars.caldav_calendar import CalDAVProvider
        assert not CalDAVProvider().is_available()
