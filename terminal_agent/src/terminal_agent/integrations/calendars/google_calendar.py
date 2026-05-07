"""Google Calendar provider using the Google Calendar API."""
import datetime
import os
from typing import Optional
from pathlib import Path
from .base_calendar import BaseCalendarProvider, CalendarEvent


class GoogleCalendarProvider(BaseCalendarProvider):
    def __init__(self, credentials_file: Optional[str] = None, token_file: str = "token.json"):
        self._credentials_file = credentials_file or os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self._token_file = token_file
        self._service = None

    @property
    def name(self) -> str:
        return "google"

    def is_available(self) -> bool:
        try:
            from google.oauth2.credentials import Credentials  # noqa: F401
            return Path(self._credentials_file).exists() or Path(self._token_file).exists()
        except ImportError:
            return False

    def _get_service(self):
        if self._service:
            return self._service
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        creds = None
        if Path(self._token_file).exists():
            creds = Credentials.from_authorized_user_file(self._token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self._credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self._token_file, "w") as f:
                f.write(creds.to_json())
        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def get_today_events(self) -> list[CalendarEvent]:
        now = datetime.datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
        return self._fetch_events(start, end)

    def get_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=days_ahead)
        return self._fetch_events(now, end)

    def _fetch_events(self, start: datetime.datetime, end: datetime.datetime) -> list[CalendarEvent]:
        try:
            svc = self._get_service()
            result = svc.events().list(
                calendarId="primary",
                timeMin=start.isoformat() + "Z",
                timeMax=end.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = []
            for item in result.get("items", []):
                start_raw = item["start"].get("dateTime", item["start"].get("date"))
                end_raw = item["end"].get("dateTime", item["end"].get("date"))
                start_dt = datetime.datetime.fromisoformat(start_raw.rstrip("Z"))
                end_dt = datetime.datetime.fromisoformat(end_raw.rstrip("Z"))
                events.append(CalendarEvent(
                    title=item.get("summary", "Untitled"),
                    start=start_dt,
                    end=end_dt,
                    location=item.get("location", ""),
                    description=item.get("description", ""),
                    event_id=item.get("id", ""),
                ))
            return events
        except Exception as e:
            print(f"Google Calendar error: {e}")
            return []

    def create_event(self, event: CalendarEvent) -> bool:
        try:
            svc = self._get_service()
            body = {
                "summary": event.title,
                "location": event.location,
                "description": event.description,
                "start": {"dateTime": event.start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": event.end.isoformat(), "timeZone": "UTC"},
            }
            svc.events().insert(calendarId="primary", body=body).execute()
            return True
        except Exception as e:
            print(f"Google Calendar create error: {e}")
            return False
