import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

class GoogleCalendarIntegration:
    def __init__(self):
        """Initialize Google Calendar integration."""
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.creds = None
        self.service = None
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
                
        self.service = build('calendar', 'v3', credentials=self.creds)
        
    def get_events(self, max_results=10):
        """Get upcoming events from Google Calendar."""
        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'summary': event['summary'],
                    'start': start,
                    'description': event.get('description', '')
                })
                
            return formatted_events
            
        except Exception as e:
            print(f"Error getting events: {str(e)}")
            return []
            
    def create_event(self, title, date, time, duration):
        """Create a new calendar event."""
        try:
            # Parse date and time
            start_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_time = start_time + datetime.timedelta(minutes=int(duration))
            
            event = {
                'summary': title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return event
            
        except Exception as e:
            print(f"Error creating event: {str(e)}")
            return None
