"""macOS-only calendar provider using EventKit via PyObjC."""
import sys
import datetime
import threading
from typing import Optional
from .base_calendar import BaseCalendarProvider, CalendarEvent


class AppleCalendarProvider(BaseCalendarProvider):
    def __init__(self):
        self._store = None
        self._initialized = False

    def _init_store(self):
        if self._initialized:
            return
        try:
            import EventKit
            import Foundation
            self._EK = EventKit
            self._Foundation = Foundation
            self._store = EventKit.EKEventStore.alloc().init()
            self._request_access()
            self._initialized = True
        except ImportError:
            self._initialized = True  # Mark so we don't retry

    def _request_access(self):
        def noop(granted, error): pass
        self._store.requestAccessToEntityType_completion_(
            self._EK.EKEntityTypeEvent, noop
        )
        self._store.requestAccessToEntityType_completion_(
            self._EK.EKEntityTypeReminder, noop
        )

    @property
    def name(self) -> str:
        return "apple"

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            import EventKit  # noqa: F401
            return True
        except ImportError:
            return False

    def _nsdate_to_dt(self, nsdate) -> Optional[datetime.datetime]:
        if not nsdate:
            return None
        return datetime.datetime.fromtimestamp(nsdate.timeIntervalSince1970())

    def _dt_to_nsdate(self, dt: datetime.datetime):
        return self._Foundation.NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())

    def get_today_events(self) -> list[CalendarEvent]:
        self._init_store()
        if not self._store:
            return []
        try:
            now = self._Foundation.NSDate.date()
            end = now.dateByAddingTimeInterval_(24 * 3600)
            predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(now, end, None)
            raw_events = self._store.eventsMatchingPredicate_(predicate)

            results: list[CalendarEvent] = []
            for ev in raw_events:
                start = self._nsdate_to_dt(ev.startDate())
                end_dt = self._nsdate_to_dt(ev.endDate())
                results.append(CalendarEvent(
                    title=str(ev.title()),
                    start=start or datetime.datetime.now(),
                    end=end_dt or datetime.datetime.now(),
                    location=str(ev.location()) if ev.location() else "",
                    calendar=str(ev.calendar().title()),
                    event_id=str(ev.eventIdentifier()),
                    all_day=bool(ev.isAllDay()),
                ))

            # Add reminders
            results.extend(self._get_reminders_for_range(now, end))
            results.sort(key=lambda e: e.start)
            return results
        except Exception as e:
            print(f"Apple Calendar error: {e}")
            return []

    def get_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        self._init_store()
        if not self._store:
            return []
        try:
            now = self._Foundation.NSDate.date()
            end = now.dateByAddingTimeInterval_(days_ahead * 24 * 3600)
            predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(now, end, None)
            raw_events = self._store.eventsMatchingPredicate_(predicate)
            results = []
            for ev in raw_events:
                start = self._nsdate_to_dt(ev.startDate())
                end_dt = self._nsdate_to_dt(ev.endDate())
                results.append(CalendarEvent(
                    title=str(ev.title()),
                    start=start or datetime.datetime.now(),
                    end=end_dt or datetime.datetime.now(),
                    location=str(ev.location()) if ev.location() else "",
                    calendar=str(ev.calendar().title()),
                    event_id=str(ev.eventIdentifier()),
                    all_day=bool(ev.isAllDay()),
                ))
            return sorted(results, key=lambda e: e.start)
        except Exception as e:
            print(f"Apple Calendar error: {e}")
            return []

    def _get_reminders_for_range(self, ns_start, ns_end) -> list[CalendarEvent]:
        reminders: list[CalendarEvent] = []
        sem = threading.Event()

        def handler(arr):
            if arr:
                for r in arr:
                    if r.dueDate() and ns_start <= r.dueDate() <= ns_end:
                        due = self._nsdate_to_dt(r.dueDate())
                        if due:
                            reminders.append(CalendarEvent(
                                title=str(r.title()),
                                start=due,
                                end=due + datetime.timedelta(hours=1),
                                event_type="reminder",
                                completed=bool(r.isCompleted()),
                                priority=int(r.priority()),
                                event_id=str(r.calendarItemIdentifier()),
                            ))
            sem.set()

        predicate = self._store.predicateForRemindersInCalendars_(None)
        self._store.fetchRemindersMatchingPredicate_completion_(predicate, handler)
        sem.wait(timeout=5.0)
        return reminders

    def create_event(self, event: CalendarEvent) -> bool:
        self._init_store()
        if not self._store:
            return False
        try:
            ev = self._EK.EKEvent.eventWithEventStore_(self._store)
            ev.setTitle_(event.title)
            ev.setStartDate_(self._dt_to_nsdate(event.start))
            ev.setEndDate_(self._dt_to_nsdate(event.end))
            if event.location:
                ev.setLocation_(event.location)
            if event.description:
                ev.setNotes_(event.description)
            ev.setCalendar_(self._store.defaultCalendarForNewEvents())
            return bool(self._store.saveEvent_span_error_(ev, self._EK.EKSpanThisEvent, None))
        except Exception as e:
            print(f"Apple Calendar create error: {e}")
            return False
