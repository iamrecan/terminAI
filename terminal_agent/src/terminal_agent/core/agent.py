#!/usr/bin/env python3

import sys
import datetime
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from colorama import init, Fore, Style as ColoramaStyle

from ..integrations.notion_integration import NotionIntegration
from ..integrations.apple_calendar_integration import AppleCalendarIntegration
from ..integrations.ai_integration import AIAssistant
from ..integrations.voice_integration import VoiceAssistant
from ..integrations.vscode_integration import VSCodeIntegration
from ..utils.project_manager import ProjectManager

import threading
import time
import os
from dotenv import load_dotenv
import dateparser
import pytz
import json
import subprocess

# Initialize colorama for cross-platform colored output
init()

class TerminalAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv(os.path.join(os.path.dirname(__file__), "../../../config/.env"))
        
        self.session = PromptSession()
        self.running = True
        self.notion = NotionIntegration()
        try:
            self.calendar = AppleCalendarIntegration()
        except Exception as e:
            print(f"{Fore.RED}Warning: Calendar integration not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.calendar = None
            
        try:
            self.ai_key = os.getenv('GOOGLE_AI_KEY')
            if not self.ai_key:
                print(f"{Fore.YELLOW}Warning: AI Assistant not available - GOOGLE_AI_KEY not found in .env file{ColoramaStyle.RESET_ALL}")
            else:
                import google.generativeai as genai
                genai.configure(api_key=self.ai_key)
                self.ai = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            print(f"{Fore.RED}Warning: AI Assistant not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.ai = None
            
        try:
            self.voice = VoiceAssistant()
            if not hasattr(self.voice, 'microphone_available') or not self.voice.microphone_available:
                print(f"{Fore.RED}Warning: Voice Assistant initialized but microphone is not available.{ColoramaStyle.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Warning: Voice Assistant not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.voice = None
            
        self.vscode = VSCodeIntegration()
        self.project_manager = ProjectManager()
        
        self.commands = {
            'help': self.show_help,
            'exit': self.exit,
            'time': self.get_time,
            'echo': self.echo,
            'tasks': self.show_tasks,
            'events': self.show_events,
            'agenda': self.show_agenda,
            'create-event': self.create_event,
            'ask': self.ask_ai,
            'chat': self.chat_with_ai,
            'listen': self.listen,
            'speak': self.voice_speak,
            'stop': self.voice_stop,
            'conversation': self.conversation,
            'open-vscode': self.handle_open_vscode,
            'terminal': self.handle_terminal,
            'run': self.handle_run_command,
            'project': self.start_project_setup,
        }
        
        # Custom prompt style
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
        })

    def show_help(self, *args):
        """Show available commands and their descriptions."""
        print(f"\n{Fore.GREEN}Available commands:{ColoramaStyle.RESET_ALL}")
        print(f"  help    - Show this help message")
        print(f"  exit    - Exit the agent")
        print(f"  time    - Show current time")
        print(f"  echo    - Echo back your message")
        print(f"  tasks   - Show today's tasks from Notion")
        print(f"  events  - Show today's events from Apple Calendar")
        print(f"  agenda  - Show combined tasks and events for today")
        print(f"  create-event - Create a new calendar event (Usage: create-event 'Title' 'YYYY-MM-DD HH:MM' 'YYYY-MM-DD HH:MM' ['Location'] ['Description'])")
        print(f"  ask     - Ask a one-time question to AI (e.g., 'ask what is Python?')")
        print(f"  chat    - Start or continue an interactive chat with AI")
        print(f"  listen  - Start voice recognition")
        print(f"  speak   - Convert text to speech (e.g., 'speak hello')")
        print(f"  stop    - Stop voice recognition")
        print(f"  conversation - Start an interactive conversation mode")
        print(f"  open vscode - Open VS Code")
        print(f"  terminal - Open terminal in VS Code")
        print(f"  run - Execute a command")
        print(f"  project - Start project setup")

    def exit(self, *args):
        """Exit the agent."""
        self.running = False
        print(f"{Fore.YELLOW}Goodbye!{ColoramaStyle.RESET_ALL}")

    def get_time(self, *args):
        """Show current time."""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Fore.GREEN}Current time: {current_time}{ColoramaStyle.RESET_ALL}")

    def echo(self, *args):
        """Echo back the user's message."""
        message = ' '.join(args)
        print(f"{Fore.CYAN}You said: {message}{ColoramaStyle.RESET_ALL}")

    def show_tasks(self, *args):
        """Show today's tasks from Notion."""
        print(f"{Fore.CYAN}Today's Notion Tasks:{ColoramaStyle.RESET_ALL}")
        tasks = self.notion.get_tasks_for_today()
        print(tasks)

    def show_events(self, *args):
        """Show today's events from Apple Calendar and Reminders."""
        if not self.calendar:
            print(f"{Fore.RED}Calendar integration not available{ColoramaStyle.RESET_ALL}")
            return
            
        events = self.calendar.get_today_events()
        if not events:
            print(f"{Fore.YELLOW}No events or reminders scheduled for today{ColoramaStyle.RESET_ALL}")
            return
            
        print(f"\n{Fore.GREEN}Today's Schedule:{ColoramaStyle.RESET_ALL}")
        
        current_time = datetime.datetime.now().astimezone()
        
        for item in events:
            if item['type'] == 'event':
                start_time = item['start'].strftime('%H:%M')
                end_time = item['end'].strftime('%H:%M')
                location = f" @ {item['location']}" if item['location'] else ""
                
                # Highlight current events
                if item['start'] <= current_time <= item['end']:
                    print(f"{Fore.GREEN}[CURRENT] {start_time}-{end_time}: {item['title']}{location}{ColoramaStyle.RESET_ALL}")
                else:
                    print(f"{start_time}-{end_time}: {item['title']}{location}")
                    
            elif item['type'] == 'reminder':
                due_time = item['start'].strftime('%H:%M')
                status = "[✓]" if item.get('completed', False) else "[pending]"
                priority = "❗" * item.get('priority', 0)  # Show priority with exclamation marks
                
                if item.get('completed', False):
                    print(f"{Fore.GREEN}{due_time}: {status} {item['title']} {priority}{ColoramaStyle.RESET_ALL}")
                elif item['start'] < current_time:
                    print(f"{Fore.RED}{due_time}: {status} {item['title']} {priority} (OVERDUE){ColoramaStyle.RESET_ALL}")
                else:
                    print(f"{due_time}: {status} {item['title']} {priority}")

    def show_agenda(self, *args):
        """Show combined tasks and events for today."""
        if self.notion:
            print(f"\n{Fore.BLUE}Today's Tasks from Notion:{ColoramaStyle.RESET_ALL}")
            self.show_tasks()
            
        if self.calendar:
            print(f"\n{Fore.GREEN}Today's Events from Calendar:{ColoramaStyle.RESET_ALL}")
            self.show_events()

    def create_event(self, *args):
        """Create a new calendar event."""
        if not self.calendar:
            print(f"{Fore.RED}Calendar integration not available{ColoramaStyle.RESET_ALL}")
            return
            
        if len(args) < 1:
            self._show_event_help()
            return
            
        # Join all arguments into a single string for natural language processing
        event_text = ' '.join(args)
        
        # Use AI-powered resolution for natural language understanding
        self._resolve_event_creation_with_ai(event_text)
            
    def _resolve_event_creation_with_ai(self, user_input: str):
        """Use AI to understand and resolve event creation issues"""
        if not self.ai:
            print(f"{Fore.RED}AI assistant not available for problem resolution{ColoramaStyle.RESET_ALL}")
            return

        try:
            print(f"{Fore.CYAN}🤖 Understanding your request...{ColoramaStyle.RESET_ALL}")
            
            # First, ask AI to extract structured information
            analysis_prompt = f"""You are a calendar assistant. Parse this event request and extract event details.
            Request: {user_input}
            Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
            
            Respond with ONLY a JSON object (no other text) containing these exact fields:
            {{
                "title": "clear event title",
                "start_time": "specific date and time (YYYY-MM-DD HH:mm)",
                "duration_minutes": number of minutes (default 60 if not specified),
                "location": "location if mentioned, otherwise empty string",
                "description": "any additional details, otherwise empty string"
            }}

            Rules for parsing:
            1. For title, use the main topic/purpose of the meeting
            2. For time, if only time is given (e.g., "2pm"), assume today
            3. For relative times (e.g., "tomorrow", "in 2 hours"), calculate the actual date/time
            4. Default duration is 60 minutes if not specified
            5. Extract any location mentioned after words like "at", "in", "@"
            6. Put any remaining context in description
            
            Example input: "Meeting with John tomorrow at 2pm at Starbucks to discuss project"
            Example output: {{"title": "Meeting with John", "start_time": "2025-01-20 14:00", "duration_minutes": 60, "location": "Starbucks", "description": "to discuss project"}}
            """
            
            # Get AI's interpretation
            analysis = self.ai.generate_content(analysis_prompt)
            
            event_info = None
            try:
                event_info = json.loads(analysis.text)
                if "error" in event_info:
                    print(f"{Fore.RED}Error: {event_info['error']}{ColoramaStyle.RESET_ALL}")
                    return
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract just the JSON part
                json_start = analysis.text.find('{')
                json_end = analysis.text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = analysis.text[json_start:json_end]
                    event_info = json.loads(json_str)
                else:
                    print(f"{Fore.RED}Error: Could not understand the event details. Please try again with a clearer description.{ColoramaStyle.RESET_ALL}")
                    print("Example: 'Meeting with John tomorrow at 2pm'")
                    return

            # Parse start time
            start_date = datetime.datetime.strptime(event_info['start_time'], '%Y-%m-%d %H:%M')
            # Calculate end time based on duration
            duration = int(event_info.get('duration_minutes', 60))
            end_date = start_date + datetime.timedelta(minutes=duration)
            
            # Verify the dates make sense
            now = datetime.datetime.now()
            if start_date < now:
                print(f"{Fore.YELLOW}Warning: The start time is in the past. Would you like to:")
                print("1. Schedule it anyway")
                print("2. Schedule it for the same time tomorrow")
                print("3. Cancel")
                choice = input("Choose (1-3): ").strip()
                
                if choice == "2":
                    # Move to tomorrow, same time
                    delta = datetime.timedelta(days=1)
                    start_date += delta
                    end_date += delta
                elif choice != "1":
                    return
            
            # Create the event
            success = self.calendar.create_event(
                event_info['title'],
                start_date,
                end_date,
                event_info.get('location', ''),
                event_info.get('description', '')
            )
            
            if success:
                print(f"\n{Fore.GREEN}Successfully created event:{ColoramaStyle.RESET_ALL}")
                print(f"  Title: {event_info['title']}")
                print(f"  Start: {start_date.strftime('%Y-%m-%d %H:%M')}")
                print(f"  End: {end_date.strftime('%Y-%m-%d %H:%M')}")
                if event_info.get('location'):
                    print(f"  Location: {event_info['location']}")
                if event_info.get('description'):
                    print(f"  Description: {event_info['description']}")
            else:
                print(f"{Fore.RED}Failed to create the event{ColoramaStyle.RESET_ALL}")
                
        except ValueError as e:
            print(f"{Fore.RED}Error: Could not understand the time format. Please try again.{ColoramaStyle.RESET_ALL}")
            print(f"Details: {str(e)}")
        except Exception as e:
            print(f"{Fore.RED}Unexpected error: {str(e)}{ColoramaStyle.RESET_ALL}")
            
    def _show_event_help(self):
        """Show help for event creation"""
        print(f"\n{Fore.GREEN}Event Creation Help:{ColoramaStyle.RESET_ALL}")
        print("\nBasic Usage:")
        print("  create-event 'Title' 'Start Time' 'End Time' ['Location'] ['Description'] ['calendar=CalendarName']")
        print("\nQuick Format:")
        print("  create-event quick 'Meeting in 2 hours for 1 hour'")
        print("\nTime Formats Supported:")
        print("  - Exact: '2025-01-20 14:00'")
        print("  - Natural: 'tomorrow at 2pm'")
        print("  - Relative: 'in 2 hours'")
        print("  - Short: '14:00' (today's date)")
        print("\nExamples:")
        print("  create-event 'Team Meeting' 'tomorrow 2pm' '3pm'")
        print("  create-event 'Lunch' '12:00' '13:00' 'Cafe'")
        print("  create-event 'Weekly Sync' 'next monday 10am' '11am' 'Room 1' 'Weekly team sync' 'calendar=Work'")
        print("  create-event quick 'Call John in 30 minutes for 1 hour'")
            
    def ask_ai(self, *args):
        """Ask a one-time question to the AI."""
        if not self.ai:
            print(f"{Fore.RED}AI Assistant not available. Please check your API key.{ColoramaStyle.RESET_ALL}")
            return
            
        question = ' '.join(args)
        if not question:
            print(f"{Fore.YELLOW}Please provide a question after 'ask'{ColoramaStyle.RESET_ALL}")
            return
            
        print(f"{Fore.CYAN}Asking AI: {question}{ColoramaStyle.RESET_ALL}")
        response = self.ai.generate_content(question)
        print(f"\n{Fore.GREEN}AI Response:{ColoramaStyle.RESET_ALL}")
        print(response.text)

    def chat_with_ai(self, *args):
        """Start or continue an interactive chat with AI"""
        if not self.ai:
            print(f"{Fore.RED}AI assistant not available{ColoramaStyle.RESET_ALL}")
            return
            
        try:
            print(f"\n{Fore.CYAN}Starting chat session... (Type 'exit' to end){ColoramaStyle.RESET_ALL}")
            
            while True:
                try:
                    user_input = input(f"{Fore.CYAN}You: {ColoramaStyle.RESET_ALL}")
                    
                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        print(f"{Fore.GREEN}Chat session ended.{ColoramaStyle.RESET_ALL}")
                        break
                        
                    response = self.ai.generate_content(user_input)
                    print(f"{Fore.GREEN}Assistant: {response.text}{ColoramaStyle.RESET_ALL}")
                    
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}Chat session interrupted.{ColoramaStyle.RESET_ALL}")
                    break
                except Exception as e:
                    print(f"{Fore.RED}Error in chat: {str(e)}{ColoramaStyle.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}Error starting chat: {str(e)}{ColoramaStyle.RESET_ALL}")

    def voice_command_checker(self):
        """Background thread to check for voice commands"""
        while self.voice and self.voice.listening:
            text = self.voice.listen()
            if text:
                if text.lower() in ["stop", "exit", "quit", "bye"]:
                    self.voice.stop_listening()
                    self.voice.stop_conversation()
                    self.voice.speak("Goodbye! Stopping voice commands.")
                    break
                else:
                    print(f"\nRecognized: {text}")
                    self.handle_voice_command(text)
                    
    def handle_voice_command(self, command):
        """Handle a voice command"""
        try:
            if not command:
                return
                
            print(f"\n{Fore.CYAN}You said: {command}{ColoramaStyle.RESET_ALL}")
            
            # Check for specific commands
            command_lower = command.lower()
            
            if command_lower in ['stop', 'exit', 'quit', 'bye']:
                self.voice.stop_listening()
                self.voice.stop_conversation()
                self.voice.speak("Goodbye! Stopping voice commands.")
                return
                
            if 'time' in command_lower:
                current_time = datetime.datetime.now().strftime('%I:%M %p')
                response = f"The current time is {current_time}"
                print(f"{Fore.GREEN}Assistant: {response}{ColoramaStyle.RESET_ALL}")
                self.voice.speak(response)
                return
                
            if 'events' in command_lower:
                self.show_events()
                return
                
            if 'tasks' in command_lower:
                self.show_tasks()
                return
                
            if 'agenda' in command_lower:
                self.show_agenda()
                return
                
            # For other commands, use AI
            if self.ai:
                response = self.ai.generate_content(command)
                print(f"{Fore.GREEN}Assistant: {response.text}{ColoramaStyle.RESET_ALL}")
                self.voice.speak(response.text)
            else:
                response = "I'm sorry, I can't process that command right now."
                print(f"{Fore.RED}Assistant: {response}{ColoramaStyle.RESET_ALL}")
                self.voice.speak(response)
                
        except Exception as e:
            print(f"{Fore.RED}Error handling voice command: {str(e)}{ColoramaStyle.RESET_ALL}")
            self.voice.speak("Sorry, I encountered an error processing that command.")
            
    def conversation(self, *args):
        """Start a conversation mode with voice"""
        if not self.voice:
            print(f"{Fore.RED}Voice assistant not available{ColoramaStyle.RESET_ALL}")
            return
            
        print(f"\n{Fore.CYAN}Starting conversation mode... Say 'stop', 'exit', 'quit', or 'bye' to end.{ColoramaStyle.RESET_ALL}")
        self.voice.start_conversation()
        
        # Start voice command checker in a separate thread
        checker_thread = threading.Thread(target=self.voice_command_checker)
        checker_thread.daemon = True
        checker_thread.start()
        
        try:
            while self.voice.is_conversing and self.voice.listening:
                time.sleep(0.1)  # Prevent CPU hogging
                
            print(f"\n{Fore.GREEN}Conversation ended.{ColoramaStyle.RESET_ALL}")
        except KeyboardInterrupt:
            self.voice.stop_conversation()
            print("\nConversation stopped by user")
        except Exception as e:
            print(f"\nError in conversation: {str(e)}")
        finally:
            self.voice.stop_conversation()
            
    def listen(self, *args):
        """Start voice recognition"""
        if not self.voice:
            print(f"{Fore.RED}Voice assistant not available{ColoramaStyle.RESET_ALL}")
            return
            
        if not self.ai:
            print(f"{Fore.RED}AI assistant not available for voice commands{ColoramaStyle.RESET_ALL}")
            return
            
        print(f"{Fore.CYAN}Starting voice recognition... (Say 'stop' to end){ColoramaStyle.RESET_ALL}")
        self.voice.start_listening()
        
        # Start voice command checker in a separate thread
        checker_thread = threading.Thread(target=self.voice_command_checker)
        checker_thread.daemon = True
        checker_thread.start()
        
        try:
            while self.voice.listening:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Voice recognition interrupted.{ColoramaStyle.RESET_ALL}")
            self.voice.stop_listening()

    def voice_stop(self, *args):
        """Stop voice recognition"""
        if not self.voice:
            print(f"{Fore.RED}Voice assistant not available{ColoramaStyle.RESET_ALL}")
            return
            
        print(f"{Fore.CYAN}Stopping voice recognition...{ColoramaStyle.RESET_ALL}")
        self.voice.stop_listening()

    def voice_speak(self, *args):
        """Convert text to speech"""
        if not self.voice:
            print(f"{Fore.RED}Voice assistant not available{ColoramaStyle.RESET_ALL}")
            return
            
        text = ' '.join(args)
        if not text:
            print(f"{Fore.YELLOW}Please provide text to speak{ColoramaStyle.RESET_ALL}")
            return
            
        self.voice.speak(text)

    def handle_open_vscode(self, args=None):
        """Handle opening VS Code"""
        path = args[0] if args else None
        if self.vscode.open_vscode(path):
            self.voice.speak("VS Code opened successfully")
        else:
            self.voice.speak("Failed to open VS Code")
            
    def handle_terminal(self, args=None):
        """Handle opening terminal in VS Code"""
        directory = args[0] if args else None
        if self.vscode.open_terminal(directory):
            self.voice.speak("Terminal opened in VS Code")
        else:
            self.voice.speak("Failed to open terminal")
            
    def handle_run_command(self, args):
        """Handle running a command"""
        if not args:
            self.voice.speak("No command specified")
            return
            
        command = ' '.join(args)
        result = self.vscode.execute_command(command)
        
        if result['success']:
            self.voice.speak(f"Command executed successfully: {result['stdout']}")
        else:
            self.voice.speak(f"Command failed: {result['stderr']}")
            
    def start_project_setup(self, *args):
        """Start project setup conversation"""
        self.project_manager.start_conversation()

    def process_command(self, command_input):
        """Process the user's command."""
        if not command_input:
            return

        parts = command_input.split()
        command = parts[0].lower()
        args = parts[1:]

        if command in self.commands:
            self.commands[command](*args)
        else:
            print(f"{Fore.RED}Unknown command: {command}. Type 'help' for available commands.{ColoramaStyle.RESET_ALL}")

    def run(self):
        """Main loop of the agent."""
        print(f"{Fore.GREEN}Welcome to Terminal Agent!{ColoramaStyle.RESET_ALL}")
        print(f"{Fore.GREEN}Type 'help' for available commands.{ColoramaStyle.RESET_ALL}")

        while self.running:
            try:
                user_input = self.session.prompt('agent> ', style=self.style)
                self.process_command(user_input.strip())
            except KeyboardInterrupt:
                continue
            except EOFError:
                self.exit()
            except Exception as e:
                print(f"{Fore.RED}Error: {str(e)}{ColoramaStyle.RESET_ALL}")

def main():
    """Entry point for the terminal agent."""
    try:
        agent = TerminalAgent()
        agent.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
