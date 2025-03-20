import subprocess
import datetime
import json
from typing import List, Dict
import Foundation
import EventKit
import objc
from PyObjCTools import AppHelper
import threading

class AppleCalendarIntegration:
    def __init__(self):
        self.store = EventKit.EKEventStore.alloc().init()
        self._request_access()
        
    def _request_access(self):
        """Request access to Calendar and Reminders"""
        def handle_calendar_auth(granted: bool, error: Foundation.NSError) -> None:
            if not granted:
                print(f"Calendar access denied: {error}")
                
        def handle_reminder_auth(granted: bool, error: Foundation.NSError) -> None:
            if not granted:
                print(f"Reminders access denied: {error}")
        
        # Request Calendar access
        self.store.requestAccessToEntityType_completion_(
            EventKit.EKEntityTypeEvent,
            handle_calendar_auth
        )
        
        # Request Reminders access
        self.store.requestAccessToEntityType_completion_(
            EventKit.EKEntityTypeReminder,
            handle_reminder_auth
        )

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

    def _nsdate_to_datetime(self, nsdate) -> datetime.datetime:
        """Convert NSDate to Python datetime"""
        if not nsdate:
            return None
        timestamp = nsdate.timeIntervalSince1970()
        return datetime.datetime.fromtimestamp(timestamp)
        
    def _datetime_to_nsdate(self, dt: datetime.datetime) -> Foundation.NSDate:
        """Convert Python datetime to NSDate"""
        if not dt:
            return None
        timestamp = dt.timestamp()
        return Foundation.NSDate.dateWithTimeIntervalSince1970_(timestamp)

    def get_calendar_events(self, days_ahead: int = 7) -> List[Dict]:
        """Get calendar events for the next N days"""
        try:
            # Create date range
            now = Foundation.NSDate.date()
            end_date = now.dateByAddingTimeInterval_(days_ahead * 24 * 60 * 60)
            
            # Create predicate for date range
            predicate = self.store.predicateForEventsWithStartDate_endDate_calendars_(
                now,
                end_date,
                None  # None means all calendars
            )
            
            # Fetch events
            events = self.store.eventsMatchingPredicate_(predicate)
            
            # Convert to Python dict
            result = []
            for event in events:
                start_dt = self._nsdate_to_datetime(event.startDate())
                end_dt = self._nsdate_to_datetime(event.endDate())
                
                result.append({
                    'title': str(event.title()),
                    'start': start_dt.isoformat() if start_dt else None,
                    'end': end_dt.isoformat() if end_dt else None,
                    'location': str(event.location()) if event.location() else '',
                    'calendar': str(event.calendar().title()),
                    'notes': str(event.notes()) if event.notes() else '',
                    'url': str(event.URL()) if event.URL() else '',
                    'all_day': bool(event.isAllDay()),
                    'id': str(event.eventIdentifier())
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting calendar events: {str(e)}")
            return []

    def get_reminders(self, days_ahead: int = 7) -> List[Dict]:
        """Get reminders for the next N days"""
        try:
            # Create date range
            now = Foundation.NSDate.date()
            end_date = now.dateByAddingTimeInterval_(days_ahead * 24 * 60 * 60)
            
            # Create predicate for date range
            predicate = self.store.predicateForRemindersInCalendars_(None)  # None means all calendars
            
            # Fetch reminders
            reminders = []
            reminder_semaphore = threading.Event()
            
            def completion_handler(remindersArray):
                if remindersArray:
                    for reminder in remindersArray:
                        if reminder.dueDate():  # Only include reminders with due dates
                            due_date = reminder.dueDate()
                            if now <= due_date <= end_date:
                                due_dt = self._nsdate_to_datetime(due_date)
                                reminders.append({
                                    'title': str(reminder.title()),
                                    'due_date': due_dt.isoformat() if due_dt else None,
                                    'completed': bool(reminder.isCompleted()),
                                    'priority': int(reminder.priority()),
                                    'notes': str(reminder.notes()) if reminder.notes() else '',
                                    'list': str(reminder.calendar().title()),
                                    'id': str(reminder.calendarItemIdentifier())
                                })
                reminder_semaphore.set()
            
            # Start async fetch
            self.store.fetchRemindersMatchingPredicate_completion_(
                predicate,
                completion_handler
            )
            
            # Wait for completion with timeout
            reminder_semaphore.wait(timeout=5.0)  # Wait up to 5 seconds
            
            return reminders
            
        except Exception as e:
            print(f"Error getting reminders: {str(e)}")
            return []

    def get_today_events(self) -> List[Dict]:
        """Get today's calendar events and reminders"""
        try:
            # Get calendar events
            today_start = Foundation.NSDate.date()
            today_end = today_start.dateByAddingTimeInterval_(24 * 60 * 60)  # Next 24 hours
            
            # Create predicate for today's events
            predicate = self.store.predicateForEventsWithStartDate_endDate_calendars_(
                today_start,
                today_end,
                None
            )
            
            # Fetch events
            events = self.store.eventsMatchingPredicate_(predicate)
            
            # Get reminders
            reminders = []
            reminder_semaphore = threading.Event()
            
            def reminder_completion_handler(remindersArray):
                if remindersArray:
                    for reminder in remindersArray:
                        if reminder.dueDate():
                            due_date = reminder.dueDate()
                            if today_start <= due_date <= today_end:
                                due_dt = self._nsdate_to_datetime(due_date)
                                end_dt = due_dt + datetime.timedelta(hours=1) if due_dt else None
                                reminders.append({
                                    'type': 'reminder',
                                    'title': str(reminder.title()),
                                    'start': due_dt.isoformat() if due_dt else None,
                                    'end': end_dt.isoformat() if end_dt else None,
                                    'completed': bool(reminder.isCompleted()),
                                    'priority': int(reminder.priority())
                                })
                reminder_semaphore.set()
            
            # Start async reminder fetch
            reminder_predicate = self.store.predicateForRemindersInCalendars_(None)
            self.store.fetchRemindersMatchingPredicate_completion_(
                reminder_predicate,
                reminder_completion_handler
            )
            
            # Wait for reminders with timeout
            reminder_semaphore.wait(timeout=5.0)
            
            # Process calendar events
            all_items = []
            for event in events:
                start_dt = self._nsdate_to_datetime(event.startDate())
                end_dt = self._nsdate_to_datetime(event.endDate())
                
                all_items.append({
                    'type': 'event',
                    'title': str(event.title()),
                    'start': start_dt.isoformat() if start_dt else None,
                    'end': end_dt.isoformat() if end_dt else None,
                    'location': str(event.location()) if event.location() else '',
                    'calendar': str(event.calendar().title())
                })
            
            # Add reminders to items
            all_items.extend(reminders)
            
            # Sort all items by start time
            all_items.sort(key=lambda x: x['start'] if x['start'] else '')
            
            if not all_items:
                print("No events or reminders scheduled for today")
                
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
                    location: str = "", notes: str = "", calendar_name: str = "") -> bool:
        """Create a new calendar event"""
        try:
            # Create new event
            event = EventKit.EKEvent.eventWithEventStore_(self.store)
            
            # Set basic properties
            event.setTitle_(title)
            event.setStartDate_(self._datetime_to_nsdate(start_date))
            event.setEndDate_(self._datetime_to_nsdate(end_date))
            
            if location:
                event.setLocation_(location)
            if notes:
                event.setNotes_(notes)
                
            # Find calendar
            if calendar_name:
                calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
                calendar = None
                for cal in calendars:
                    if str(cal.title()) == calendar_name:
                        calendar = cal
                        break
                if not calendar:
                    print(f"Calendar '{calendar_name}' not found, using default")
                    calendar = self.store.defaultCalendarForNewEvents()
            else:
                calendar = self.store.defaultCalendarForNewEvents()
                
            # Set calendar and save
            event.setCalendar_(calendar)
            return bool(self.store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, None))
            
        except Exception as e:
            print(f"Error creating event: {str(e)}")
            return False

    def create_reminder(self, title: str, due_date: datetime.datetime,
                       notes: str = "", priority: int = 0, list_name: str = "") -> bool:
        """Create a new reminder"""
        try:
            # Create new reminder
            reminder = EventKit.EKReminder.reminderWithEventStore_(self.store)
            
            # Set basic properties
            reminder.setTitle_(title)
            reminder.setDueDate_(self._datetime_to_nsdate(due_date))
            
            if notes:
                reminder.setNotes_(notes)
            if priority:
                reminder.setPriority_(priority)
                
            # Find reminder list
            if list_name:
                lists = self.store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
                reminder_list = None
                for lst in lists:
                    if str(lst.title()) == list_name:
                        reminder_list = lst
                        break
                if not reminder_list:
                    print(f"Reminder list '{list_name}' not found, using default")
                    reminder_list = self.store.defaultCalendarForNewReminders()
            else:
                reminder_list = self.store.defaultCalendarForNewReminders()
                
            # Set list and save
            reminder.setCalendar_(reminder_list)
            return bool(self.store.saveReminder_commit_error_(reminder, True, None))
            
        except Exception as e:
            print(f"Error creating reminder: {str(e)}")
            return False

    def update_event(self, event_id: str, **kwargs) -> bool:
        """Update an existing calendar event"""
        try:
            event = self.store.eventWithIdentifier_(event_id)
            if not event:
                print(f"Event with id {event_id} not found")
                return False
                
            # Update provided fields
            if 'title' in kwargs:
                event.setTitle_(kwargs['title'])
            if 'start_date' in kwargs:
                event.setStartDate_(self._datetime_to_nsdate(kwargs['start_date']))
            if 'end_date' in kwargs:
                event.setEndDate_(self._datetime_to_nsdate(kwargs['end_date']))
            if 'location' in kwargs:
                event.setLocation_(kwargs['location'])
            if 'notes' in kwargs:
                event.setNotes_(kwargs['notes'])
                
            return bool(self.store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, None))
            
        except Exception as e:
            print(f"Error updating event: {str(e)}")
            return False

    def update_reminder(self, reminder_id: str, **kwargs) -> bool:
        """Update an existing reminder"""
        try:
            reminder = self.store.calendarItemWithIdentifier_(reminder_id)
            if not reminder or not isinstance(reminder, EventKit.EKReminder):
                print(f"Reminder with id {reminder_id} not found")
                return False
                
            # Update provided fields
            if 'title' in kwargs:
                reminder.setTitle_(kwargs['title'])
            if 'due_date' in kwargs:
                reminder.setDueDate_(self._datetime_to_nsdate(kwargs['due_date']))
            if 'notes' in kwargs:
                reminder.setNotes_(kwargs['notes'])
            if 'priority' in kwargs:
                reminder.setPriority_(kwargs['priority'])
            if 'completed' in kwargs:
                reminder.setCompleted_(kwargs['completed'])
                
            return bool(self.store.saveReminder_commit_error_(reminder, True, None))
            
        except Exception as e:
            print(f"Error updating reminder: {str(e)}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            event = self.store.eventWithIdentifier_(event_id)
            if not event:
                print(f"Event with id {event_id} not found")
                return False
                
            return bool(self.store.removeEvent_span_error_(event, EventKit.EKSpanThisEvent, None))
            
        except Exception as e:
            print(f"Error deleting event: {str(e)}")
            return False

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder"""
        try:
            reminder = self.store.calendarItemWithIdentifier_(reminder_id)
            if not reminder or not isinstance(reminder, EventKit.EKReminder):
                print(f"Reminder with id {reminder_id} not found")
                return False
                
            return bool(self.store.removeReminder_commit_error_(reminder, True, None))
            
        except Exception as e:
            print(f"Error deleting reminder: {str(e)}")
            return False
