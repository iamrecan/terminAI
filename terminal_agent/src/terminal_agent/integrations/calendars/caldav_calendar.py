"""Cross-platform CalDAV provider (Nextcloud, iCloud, Fastmail, etc.)."""
import datetime
import os
from typing import Optional
from .base_calendar import BaseCalendarProvider, CalendarEvent


class CalDAVProvider(BaseCalendarProvider):
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._url = url or os.getenv("CALDAV_URL")
        self._username = username or os.getenv("CALDAV_USERNAME")
        self._password = password or os.getenv("CALDAV_PASSWORD")
        self._calendar = None

    @property
    def name(self) -> str:
        return "caldav"

    def is_available(self) -> bool:
        if not (self._url and self._username and self._password):
            return False
        try:
            import caldav  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_calendar(self):
        if self._calendar:
            return self._calendar
        import caldav
        client = caldav.DAVClient(url=self._url, username=self._username, password=self._password)
        principal = client.principal()
        calendars = principal.calendars()
        if not calendars:
            raise RuntimeError("No CalDAV calendars found")
        self._calendar = calendars[0]
        return self._calendar

    def get_today_events(self) -> list[CalendarEvent]:
        now = datetime.datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
        return self._fetch(start, end)

    def get_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        start = datetime.datetime.now()
        end = start + datetime.timedelta(days=days_ahead)
        return self._fetch(start, end)

    def _fetch(self, start: datetime.datetime, end: datetime.datetime) -> list[CalendarEvent]:
        try:
            cal = self._get_calendar()
            raw = cal.date_search(start=start, end=end, expand=True)
            events = []
            for vevent_obj in raw:
                for component in vevent_obj.icalendar_component.walk():
                    if component.name != "VEVENT":
                        continue
                    dtstart = component.get("DTSTART")
                    dtend = component.get("DTEND")
                    if not dtstart:
                        continue
                    start_dt = dtstart.dt
                    end_dt = dtend.dt if dtend else start_dt
                    if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                        start_dt = datetime.datetime.combine(start_dt, datetime.time())
                        end_dt = datetime.datetime.combine(end_dt, datetime.time())
                    events.append(CalendarEvent(
                        title=str(component.get("SUMMARY", "Untitled")),
                        start=start_dt,
                        end=end_dt,
                        location=str(component.get("LOCATION", "")),
                        description=str(component.get("DESCRIPTION", "")),
                        event_id=str(component.get("UID", "")),
                    ))
            return sorted(events, key=lambda e: e.start)
        except Exception as e:
            print(f"CalDAV error: {e}")
            return []

    def create_event(self, event: CalendarEvent) -> bool:
        try:
            cal = self._get_calendar()
            from icalendar import Calendar, Event
            import uuid
            c = Calendar()
            e = Event()
            e.add("summary", event.title)
            e.add("dtstart", event.start)
            e.add("dtend", event.end)
            e.add("uid", str(uuid.uuid4()))
            if event.location:
                e.add("location", event.location)
            if event.description:
                e.add("description", event.description)
            c.add_component(e)
            cal.save_event(c.to_ical())
            return True
        except Exception as e:
            print(f"CalDAV create error: {e}")
            return False
