import subprocess
import datetime
import json
from typing import List, Dict

class AppleCalendarIntegration:
    def __init__(self):
        self.osascript_calendar_template = '''
        tell application "Calendar"
            set eventList to {}
            set startDate to current date
            set endDate to ((current date) + (%d * days))
            
            set allEvents to {}
            repeat with calAccount in calendars
                tell calAccount
                    set allEvents to allEvents & (every event whose start date is greater than or equal to startDate and start date is less than or equal to endDate)
                end tell
            end repeat
            
            set jsonEvents to "["
            repeat with i from 1 to count of allEvents
                set currentEvent to item i of allEvents
                set eventTitle to (get summary of currentEvent)
                set eventStart to (get start date of currentEvent)
                set eventEnd to (get end date of currentEvent)
                set eventLocation to ""
                try
                    set eventLocation to (get location of currentEvent)
                end try
                
                if i < count of allEvents then
                    set jsonEvents to jsonEvents & "{\\"title\\": \\"" & eventTitle & "\\", \\"start\\": \\"" & eventStart & "\\", \\"end\\": \\"" & eventEnd & "\\", \\"location\\": \\"" & eventLocation & "\\"}, "
                else
                    set jsonEvents to jsonEvents & "{\\"title\\": \\"" & eventTitle & "\\", \\"start\\": \\"" & eventStart & "\\", \\"end\\": \\"" & eventEnd & "\\", \\"location\\": \\"" & eventLocation & "\\"}"
                end if
            end repeat
            
            set jsonEvents to jsonEvents & "]"
            return jsonEvents
        end tell
        '''
        
        self.osascript_reminders_template = '''
        tell application "Reminders"
            set reminderList to {}
            set startDate to current date
            set endDate to ((current date) + (%d * days))
            
            set allReminders to {}
            tell default account
                repeat with remList in lists
                    set allReminders to allReminders & (every reminder in remList whose due date is greater than or equal to startDate and due date is less than or equal to endDate)
                end repeat
            end tell
            
            set jsonReminders to "["
            repeat with i from 1 to count of allReminders
                set currentReminder to item i of allReminders
                set reminderName to name of currentReminder
                set reminderDueDate to due date of currentReminder
                set reminderCompleted to completed of currentReminder
                set reminderPriority to priority of currentReminder
                
                if i < count of allReminders then
                    set jsonReminders to jsonReminders & "{\\"title\\": \\"" & reminderName & "\\", \\"due_date\\": \\"" & reminderDueDate & "\\", \\"completed\\": " & reminderCompleted & ", \\"priority\\": " & reminderPriority & "}, "
                else
                    set jsonReminders to jsonReminders & "{\\"title\\": \\"" & reminderName & "\\", \\"due_date\\": \\"" & reminderDueDate & "\\", \\"completed\\": " & reminderCompleted & ", \\"priority\\": " & reminderPriority & "}"
                end if
            end repeat
            
            set jsonReminders to jsonReminders & "]"
            return jsonReminders
        end tell
        '''

    def _run_apple_script(self, script: str) -> str:
        """Run an AppleScript and return its output"""
        try:
            process = subprocess.Popen(['osascript', '-e', script],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            output, error = process.communicate()
            
            if error:
                print(f"Error running AppleScript: {error.decode()}")
                return "[]"
                
            return output.decode()
        except Exception as e:
            print(f"Error executing AppleScript: {str(e)}")
            return "[]"

    def get_calendar_events(self, days_ahead: int = 7) -> List[Dict]:
        """Get calendar events for the next N days"""
        script = self.osascript_calendar_template % days_ahead
        result = self._run_apple_script(script)
        
        try:
            events = json.loads(result)
            # Convert date strings to datetime objects
            for event in events:
                event['start'] = datetime.datetime.strptime(event['start'], '%Y-%m-%d %H:%M:%S +0000')
                event['end'] = datetime.datetime.strptime(event['end'], '%Y-%m-%d %H:%M:%S +0000')
            return events
        except json.JSONDecodeError as e:
            print(f"Error parsing calendar events: {str(e)}")
            return []

    def get_reminders(self, days_ahead: int = 7) -> List[Dict]:
        """Get reminders for the next N days"""
        script = self.osascript_reminders_template % days_ahead
        result = self._run_apple_script(script)
        
        try:
            reminders = json.loads(result)
            # Convert date strings to datetime objects
            for reminder in reminders:
                if reminder['due_date']:
                    reminder['due_date'] = datetime.datetime.strptime(
                        reminder['due_date'], '%Y-%m-%d %H:%M:%S +0000'
                    )
            return reminders
        except json.JSONDecodeError as e:
            print(f"Error parsing reminders: {str(e)}")
            return []

    def get_today_events(self) -> List[Dict]:
        """Get today's calendar events and reminders"""
        try:
            # Get calendar events
            calendar_events = self.get_calendar_events(days_ahead=0)  # Only today's events
            
            # Get reminders
            reminders = self.get_reminders(days_ahead=0)  # Only today's reminders
            
            # Combine and sort all items
            all_items = []
            
            # Process calendar events
            for event in calendar_events:
                if isinstance(event.get('start'), str):
                    try:
                        event['start'] = datetime.datetime.strptime(event['start'], '%Y-%m-%d %H:%M:%S +0000')
                    except ValueError:
                        try:
                            event['start'] = datetime.datetime.strptime(event['start'].split('+')[0].strip(), '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
                            
                if isinstance(event.get('end'), str):
                    try:
                        event['end'] = datetime.datetime.strptime(event['end'], '%Y-%m-%d %H:%M:%S +0000')
                    except ValueError:
                        try:
                            event['end'] = datetime.datetime.strptime(event['end'].split('+')[0].strip(), '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
                
                # Convert to local time
                event['start'] = event['start'].replace(tzinfo=datetime.timezone.utc).astimezone()
                event['end'] = event['end'].replace(tzinfo=datetime.timezone.utc).astimezone()
                
                all_items.append({
                    'type': 'event',
                    'title': event['title'],
                    'start': event['start'],
                    'end': event['end'],
                    'location': event.get('location', '')
                })
            
            # Process reminders
            for reminder in reminders:
                if isinstance(reminder.get('due_date'), str):
                    try:
                        due_date = datetime.datetime.strptime(reminder['due_date'], '%Y-%m-%d %H:%M:%S +0000')
                        # Convert to local time
                        due_date = due_date.replace(tzinfo=datetime.timezone.utc).astimezone()
                        
                        all_items.append({
                            'type': 'reminder',
                            'title': reminder['title'],
                            'start': due_date,
                            'end': due_date + datetime.timedelta(hours=1),  # Set 1-hour duration for reminders
                            'completed': reminder.get('completed', False),
                            'priority': reminder.get('priority', 0)
                        })
                    except ValueError:
                        continue
            
            # Sort all items by start time
            all_items.sort(key=lambda x: x['start'])
            
            return all_items
            
        except Exception as e:
            print(f"Error getting today's events and reminders: {str(e)}")
            return []

    def get_today_reminders(self) -> List[Dict]:
        """Get today's reminders"""
        return self.get_reminders(days_ahead=1)

    def get_agenda(self, days_ahead: int = 7) -> Dict[str, List[Dict]]:
        """Get both calendar events and reminders for the specified period"""
        return {
            'events': self.get_calendar_events(days_ahead),
            'reminders': self.get_reminders(days_ahead)
        }
        
    def create_event(self, title: str, start_date: datetime.datetime, end_date: datetime.datetime, 
                    location: str = "", description: str = "", calendar_name: str = ""):
        """Create a new calendar event
        
        Args:
            title: Event title
            start_date: Start date and time
            end_date: End date and time
            location: Optional location
            description: Optional description
            calendar_name: Optional calendar name (uses default if not specified)
        """
        # Format dates for AppleScript
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        script = f'''
        tell application "Calendar"
            tell calendar "{calendar_name or 'Calendar'}"
                set newEvent to make new event with properties {{summary:"{title}", start date:date "{start_date_str}", end date:date "{end_date_str}"}}
                tell newEvent
                    set location to "{location}"
                    set description to "{description}"
                end tell
                return id of newEvent
            end tell
        end tell
        '''
        
        result = self._run_apple_script(script)
        if "Error" not in result:
            return True
        return False
