from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""
    calendar: str = ""
    event_id: str = ""
    all_day: bool = False
    event_type: str = "event"  # "event" | "reminder"
    completed: bool = False
    priority: int = 0


class BaseCalendarProvider(ABC):
    @abstractmethod
    def get_today_events(self) -> list[CalendarEvent]: ...

    @abstractmethod
    def get_events(self, days_ahead: int = 7) -> list[CalendarEvent]: ...

    @abstractmethod
    def create_event(self, event: CalendarEvent) -> bool: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
