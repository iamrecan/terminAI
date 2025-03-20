#!/usr/bin/env python3

import sys
import datetime
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from colorama import init, Fore, Style as ColoramaStyle

from ..integrations.notion_integration import NotionIntegration
from ..integrations.apple_calendar_integration import AppleCalendarIntegration
from ..integrations.ai_integration import AIAssistant
from ..integrations.voice_integration import VoiceAssistant
from ..integrations.vscode_integration import VSCodeIntegration
from ..integrations.aider_integration import AiderIntegration
from ..integrations.mcp_integration import MCPIntegration
from ..utils.project_manager import ProjectManager
from ..utils.terminal_composer import TerminalOutputComposer
from ..utils.llm_handler import LLMHandler

import threading
import time
import os
from dotenv import load_dotenv
import dateparser
import pytz
import json
import subprocess
from textwrap import dedent

# Initialize colorama for cross-platform colored output
init()

class TerminalAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv(os.path.join(os.path.dirname(__file__), "../../../config/.env"))
        
        self.session = PromptSession()
        self.running = True
        self.project_manager = ProjectManager()
        self.notion = NotionIntegration()
        try:
            self.calendar = AppleCalendarIntegration()
        except Exception as e:
            print(f"{Fore.RED}Warning: Calendar integration not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.calendar = None
            
        # Initialize AI Assistant
        try:
            self.ai_key = os.getenv('GOOGLE_AI_KEY')
            if not self.ai_key:
                print(f"{Fore.YELLOW}Warning: Google AI Assistant not available - GOOGLE_AI_KEY not found in .env file{ColoramaStyle.RESET_ALL}")
            else:
                import google.generativeai as genai
                genai.configure(api_key=self.ai_key)
                self.ai = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            print(f"{Fore.RED}Warning: Google AI Assistant not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.ai = None

        # Initialize Voice Assistant
        try:
            self.voice = VoiceAssistant()
            if not hasattr(self.voice, 'microphone_available') or not self.voice.microphone_available:
                print(f"{Fore.RED}Warning: Voice Assistant initialized but microphone is not available.{ColoramaStyle.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Warning: Voice Assistant not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.voice = None

        # Initialize MCP (with Ollama fallback)
        try:
            mcp_api_key = os.getenv('MCP_API_KEY')
            self.mcp = MCPIntegration(mcp_api_key)  # Will use Ollama if api_key is None
            
            # Test connection asynchronously
            loop = asyncio.get_event_loop()
            is_connected = loop.run_until_complete(self.mcp.connect_to_server())
            
            if not is_connected and not mcp_api_key:
                print(f"{Fore.YELLOW}Warning: MCP using local Ollama - make sure Ollama is running{ColoramaStyle.RESET_ALL}")
            elif not is_connected:
                print(f"{Fore.RED}Warning: MCP connection failed{ColoramaStyle.RESET_ALL}")
                self.mcp = None
        except Exception as e:
            print(f"{Fore.RED}Warning: MCP not available - {str(e)}{ColoramaStyle.RESET_ALL}")
            self.mcp = None
            
        self.vscode = VSCodeIntegration()
        self.project_manager = ProjectManager()
        self.aider = AiderIntegration()
        self.composer = TerminalOutputComposer()
        self.llm = LLMHandler()
        
        self.conversation_thread = None
        
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
            'conversation': self.start_conversation_thread,
            'stop conversation': self.stop_conversation,
            'open vscode': self.handle_open_vscode,
            'terminal': self.handle_terminal,
            'run': self.handle_run_command,
            'project': self.start_project_setup,
            'aider': self.start_aider,
            'aider-status': self.show_aider_status,
            'create-project': self.create_project,  # New command
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
        print(f"  create-event - Create a new calendar event (Use 'create-event' without args for help)")
        print(f"  ask     - Ask a one-time question to AI (e.g., 'ask what is Python?')")
        print(f"  chat    - Start an interactive chat with AI (Type 'exit' to end chat)")
        print(f"  listen  - Start voice recognition (Say 'stop' to end)")
        print(f"  speak   - Convert text to speech (e.g., 'speak hello')")
        print(f"  stop    - Stop voice recognition")
        print(f"  conversation - Start a conversation mode with voice")
        print(f"  stop conversation - Stop the conversation mode")
        print(f"  open vscode - Open VS Code")
        print(f"  terminal - Open terminal in VS Code")
        print(f"  run - Execute a command")
        print(f"  project - Start project setup")
        print(f"  aider - Start Aider coding assistant (or other AI assistants)")
        print(f"  aider-status - Show status of available AI coding assistants")
        print(f"  create-project - Create a new project with AI assistance")
        
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
        
        # Get current time with timezone
        current_time = datetime.datetime.now(datetime.timezone.utc).astimezone()
        local_tz = current_time.tzinfo
        
        for item in events:
            try:
                if item['type'] == 'event':
                    # Parse ISO format dates and set timezone
                    start_time = datetime.datetime.fromisoformat(item['start']).replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
                    end_time = datetime.datetime.fromisoformat(item['end']).replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
                    
                    start_str = start_time.strftime('%H:%M')
                    end_str = end_time.strftime('%H:%M')
                    location = f" @ {item['location']}" if item['location'] else ""
                    
                    # Highlight current events
                    if start_time <= current_time <= end_time:
                        print(f"{Fore.GREEN}[CURRENT] {start_str}-{end_str}: {item['title']}{location}{ColoramaStyle.RESET_ALL}")
                    else:
                        print(f"{start_str}-{end_str}: {item['title']}{location}")
                        
                elif item['type'] == 'reminder':
                    # Parse ISO format date and set timezone
                    start_time = datetime.datetime.fromisoformat(item['start']).replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
                    due_str = start_time.strftime('%H:%M')
                    
                    status = "[✓]" if item.get('completed', False) else "[pending]"
                    priority = "❗" * item.get('priority', 0)  # Show priority with exclamation marks
                    
                    if item.get('completed', False):
                        print(f"{Fore.GREEN}{due_str}: {status} {item['title']} {priority}{ColoramaStyle.RESET_ALL}")
                    elif start_time < current_time:
                        print(f"{Fore.RED}{due_str}: {status} {item['title']} {priority} (OVERDUE){ColoramaStyle.RESET_ALL}")
                    else:
                        print(f"{due_str}: {status} {item['title']} {priority}")
                        
            except (ValueError, KeyError) as e:
                print(f"{Fore.RED}Error parsing event: {item.get('title', 'Unknown')} - {str(e)}{ColoramaStyle.RESET_ALL}")
                continue

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
            print(f"{Fore.CYAN}Asking AI: {user_input}{ColoramaStyle.RESET_ALL}")
            
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
        print(f"\n{Fore.GREEN}Project Setup Help:{ColoramaStyle.RESET_ALL}")
        print("Use 'create-project' command to create a new project.")
        print("\nExample:")
        print("  create-project please create for me todo app")

    def start_conversation_thread(self, *args):
        """Start conversation in a separate thread."""
        if self.conversation_thread and self.conversation_thread.is_alive():
            print("Conversation is already running!")
            return
            
        self.conversation_thread = threading.Thread(
            target=self.conversation,
            daemon=True
        )
        self.conversation_thread.start()
        
    def stop_conversation(self, *args):
        """Stop the conversation thread."""
        if self.conversation_thread and self.conversation_thread.is_alive():
            self.voice.conversation_active = False
            self.conversation_thread.join(timeout=1)
            print("Conversation stopped.")
        else:
            print("No active conversation to stop.")
            
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

    def start_aider(self, *args):
        """Start Aider coding assistant."""
        try:
            # Clean up args - remove any 'agent>' prefix from each arg
            cleaned_args = []
            for arg in args:
                if arg.startswith('agent>'):
                    arg = arg[6:].strip()
                cleaned_args.append(arg)
                
            # Parse arguments
            assistant = 'aider'  # default
            git_dir = None
            parsed_args = []
            
            i = 0
            while i < len(cleaned_args):
                arg = cleaned_args[i]
                if arg.startswith('--assistant='):
                    assistant = arg.split('=')[1]
                elif arg.startswith('--dir='):
                    git_dir = arg.split('=')[1]
                elif arg == '--dir':
                    if i + 1 < len(cleaned_args):
                        i += 1
                        git_dir = cleaned_args[i]
                else:
                    parsed_args.append(arg)
                i += 1
                
            # Show available assistants if requested
            if '--list' in parsed_args:
                available = self.aider.list_available_assistants()
                print(f"\n{Fore.GREEN}Available AI coding assistants:{ColoramaStyle.RESET_ALL}")
                for asst in available:
                    print(f"  - {asst}")
                return
                
            # Show help if no directory specified
            if not git_dir:
                print(f"\n{Fore.GREEN}Aider Command Help:{ColoramaStyle.RESET_ALL}")
                print("Usage: aider --dir PATH [options] [files...]")
                print("\nOptions:")
                print("  --assistant=NAME    Select AI assistant (default: aider)")
                print("  --dir PATH         Set working directory")
                print("  --list             List available assistants")
                print("  --help             Show this help message")
                print("\nExample:")
                print("  aider --dir /path/to/project")
                print("\nAvailable assistants:", ', '.join(self.aider.list_available_assistants()))
                return
                
            # Start the assistant
            success = self.aider.start_assistant(
                assistant=assistant,
                git_dir=os.path.expanduser(git_dir),  # Expand ~ if present
                args=parsed_args
            )
            
            if success:
                print(f"\n{Fore.GREEN}Started {assistant} in a new terminal window{ColoramaStyle.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}Error starting Aider: {str(e)}{ColoramaStyle.RESET_ALL}")

    def show_aider_status(self, *args):
        """Show status of available AI coding assistants."""
        status = self.aider.get_assistant_status()
        
        print(f"\n{Fore.GREEN}AI Coding Assistant Status:{ColoramaStyle.RESET_ALL}")
        for name, available in status.items():
            status_str = f"{Fore.GREEN}Available{ColoramaStyle.RESET_ALL}" if available else f"{Fore.RED}Not Available{ColoramaStyle.RESET_ALL}"
            print(f"  {name}: {status_str}")

    def create_project(self, *args):
        """Create a new project with AI assistance."""
        try:
            # Parse the project description from args
            if len(args) < 4 or args[0] != 'please' or args[1] != 'create' or args[2] != 'for' or args[3] != 'me':
                print(f"\n{Fore.GREEN}Create Project Help:{ColoramaStyle.RESET_ALL}")
                print("Usage: create-project please create for me <project description>")
                print("\nExample:")
                print("  create-project please create for me todo app")
                return

            project_description = ' '.join(args[4:])
            if not project_description:
                print(f"{Fore.RED}Error: Please provide a project description{ColoramaStyle.RESET_ALL}")
                return

            # Extract project name from description
            project_name = project_description.split()[0]
            
            # Create project directory
            project_dir = os.path.join(os.getcwd(), project_name)
            os.makedirs(project_dir, exist_ok=True)
            
            # Create basic structure
            os.makedirs(os.path.join(project_dir, 'src'), exist_ok=True)
            os.makedirs(os.path.join(project_dir, 'tests'), exist_ok=True)
            
            # Create requirements.txt
            with open(os.path.join(project_dir, 'requirements.txt'), 'w') as f:
                f.write('flask\nflask-sqlalchemy\npython-dotenv\n')
            
            # Create README.md
            with open(os.path.join(project_dir, 'README.md'), 'w') as f:
                f.write(f'# {project_name}\n\n{project_description}\n')
            
            print(f"\n{Fore.GREEN}Created project structure:{ColoramaStyle.RESET_ALL}")
            print(f"  {project_dir}/")
            print(f"  ├── src/")
            print(f"  ├── tests/")
            print(f"  ├── requirements.txt")
            print(f"  └── README.md")
            
            # Get next steps from LLM
            if self.ai:
                prompt = f"I just created a new {project_description} project. Give me the next steps to set up the development environment and start working on it. Format the response as a numbered list with commands, be concise."
                response = self.ai.generate_content(prompt)
                if response and response.text:
                    print(f"\n{Fore.GREEN}Next steps (AI suggested):{ColoramaStyle.RESET_ALL}")
                    print(response.text)
                else:
                    self._show_default_next_steps(project_name)
            else:
                self._show_default_next_steps(project_name)
            
        except Exception as e:
            print(f"{Fore.RED}Error creating project: {str(e)}{ColoramaStyle.RESET_ALL}")
            
    def _show_default_next_steps(self, project_name):
        """Show default next steps when AI is not available."""
        print(f"\n{Fore.GREEN}Next steps:{ColoramaStyle.RESET_ALL}")
        print(f"  1. cd {project_name}")
        print(f"  2. python -m venv venv")
        print(f"  3. source venv/bin/activate")
        print(f"  4. pip install -r requirements.txt")




def get_project_info():
    print("=== New Project Setup ===\\n")
    
    name = {repr(project_name)}
    if not name:
        name = input('Enter project name: ')
        
    type_name = {repr(project_type)}
    if not type_name:
        type_name = input('Enter project type (web, cli, library, etc.): ')
        
    print("\\nEnter project description (what will this project do?):")
    description = input('> ')
    
    # Use existing API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("\\nEnter your Google API key (get one from https://makersuite.google.com/app/apikey):")
        api_key = input('> ')
        
        if not api_key.startswith('AI'):
            print("\\nWarning: API key format looks incorrect. It should start with 'AI'")
            if not input('Continue anyway? (y/n): ').lower().startswith('y'):
                raise Exception("Setup cancelled due to invalid API key format")
    
        with open('.env', 'w') as f:
            f.write(f"GOOGLE_API_KEY={{{api_key}}}\\n")
    
    return name, type_name, description

def get_project_roadmap(name, type_name, description):
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    
    if not api_key:
        raise Exception("GOOGLE_API_KEY not found in .env file")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        raise Exception(f"Failed to configure Gemini API: {{str(e)}}")
    
    tech_stack = ""
    if type_name == "fullstack":
        tech_stack = """
Technical Stack:
- Backend: Python (FastAPI)
- Frontend: TypeScript + React
- Database: PostgreSQL
- API: RESTful + OpenAPI
"""
    elif type_name == "web":
        tech_stack = """
Technical Stack:
- Python (FastAPI)
- Database: SQLite/PostgreSQL
- Templates: Jinja2
"""
    
    prompt = f"""You are a project planning assistant. Generate a project roadmap in STRICT JSON format.
DO NOT include any explanatory text or markdown, ONLY output valid JSON.
The JSON must match this EXACT structure:

{{
    "overview": "Brief project description",
    "architecture": {{
        "component_name": "component description"
    }},
    "features": [
        {{
            "name": "feature name",
            "description": "feature description",
            "priority": "high|medium|low"
        }}
    ],
    "phases": [
        {{
            "name": "phase name",
            "tasks": ["task 1", "task 2"],
            "duration": "time estimate"
        }}
    ],
    "file_structure": {{
        "file/path": "file contents or description"
    }},
    "dependencies": [
        "package>=version"
    ],
    "testing": {{
        "strategy": "testing approach",
        "types": ["test type 1", "test type 2"]
    }},
    "deployment": {{
        "requirements": ["requirement 1", "requirement 2"],
        "steps": ["step 1", "step 2"]
    }}
}}

Project Details:
Name: {{name}}
Type: {{type_name}}
Description: {{description}}
{{tech_stack}}

Remember:
1. ONLY output valid JSON
2. Follow the EXACT structure shown above
3. DO NOT include any other text or explanation
4. Make sure all JSON keys and values are properly quoted
5. Include realistic package versions in dependencies
6. For file_structure, include actual starter code for key files
"""
    
    response = model.generate_content(prompt)
    
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini response: {{str(e)}}")
        print("Response text:", response.text)
        print("Falling back to basic structure...")
        
        return {{
            "overview": description,
            "architecture": {{
                "frontend": "React + TypeScript based SPA" if type_name == "fullstack" else "Simple web interface",
                "backend": "Python FastAPI REST server",
                "database": "SQLite for development, PostgreSQL for production"
            }},
            "features": [
                {{
                    "name": "Basic Setup",
                    "description": "Initial project structure and configuration",
                    "priority": "high"
                }}
            ],
            "phases": [
                {{
                    "name": "Setup",
                    "tasks": ["Initialize project", "Setup development environment"],
                    "duration": "1 week"
                }}
            ],
            "file_structure": {{
                "src/main.py": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n\\n@app.get('/')\\ndef read_root():\\n    return {{'message': 'Hello World'}}",
                "src/models.py": "from sqlalchemy import Column, Integer, String\\nfrom database import Base\\n\\nclass Item(Base):\\n    __tablename__ = 'items'\\n    id = Column(Integer, primary_key=True)\\n    title = Column(String)",
                "src/database.py": "from sqlalchemy import create_engine\\nfrom sqlalchemy.ext.declarative import declarative_base\\n\\nengine = create_engine('sqlite:///./test.db')\\nBase = declarative_base()"
            }},
            "dependencies": [
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0",
                "sqlalchemy>=2.0.0",
                "python-dotenv>=1.0.0",
                "pytest>=7.0.0"
            ],
            "testing": {{
                "strategy": "Unit tests with pytest",
                "types": ["unit", "integration"]
            }},
            "deployment": {{
                "requirements": ["Python 3.8+", "PostgreSQL"],
                "steps": ["Setup virtual environment", "Install dependencies", "Run migrations", "Start server"]
            }}
        }}

def create_project_structure(roadmap, name, type_name):
    os.makedirs('src', exist_ok=True)
    os.makedirs('tests', exist_ok=True)
    os.makedirs('docs', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    if type_name == "fullstack":
        os.makedirs('frontend', exist_ok=True)
        os.makedirs('frontend/src', exist_ok=True)
        os.makedirs('backend', exist_ok=True)
        os.makedirs('backend/src', exist_ok=True)
        
        with open('frontend/package.json', 'w') as f:
            f.write("""{{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {{
    "@types/node": "^16.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^4.9.0",
    "axios": "^1.3.0",
    "@mantine/core": "^6.0.0",
    "@mantine/hooks": "^6.0.0"
  }},
  "scripts": {{
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }}
}}""")
    
    with open('README.md', 'w') as f:
        f.write(f"# {{name}}\\n\\n{{roadmap['overview']}}")
    
    with open('requirements.txt', 'w') as f:
        for dep in roadmap['dependencies']:
            f.write(dep + "\\n")
    
    for path, content in roadmap['file_structure'].items():
        full_path = os.path.join(os.getcwd(), path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(str(content))
            
    print("Project structure created successfully!")

def start_project(name, type_name):
    print("\\nInstalling dependencies...")
    
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    
    if type_name == "fullstack":
        os.chdir('frontend')
        subprocess.run(['npm', 'install'], check=True)
        
        backend_dir = os.path.join(os.getcwd(), '..', 'backend')
        backend_cmd = f"cd {{backend_dir}} && {{sys.executable}} -m uvicorn src.main:app --reload --port 8000"
        
        if sys.platform == 'darwin':
            osascript = f'tell application "Terminal" to do script "{{backend_cmd}}"'
            subprocess.run(['osascript', '-e', osascript], check=True)
        
        frontend_dir = os.getcwd()
        frontend_cmd = f"cd {{frontend_dir}} && npm start"
        
        if sys.platform == 'darwin':
            osascript = f'tell application "Terminal" to do script "{{frontend_cmd}}"'
            subprocess.run(['osascript', '-e', osascript], check=True)
        
        print("\\nFullstack project started!")
        print("Backend running at: http://localhost:8000")
        print("Frontend running at: http://localhost:3000")
        
    elif type_name == "web":
        current_dir = os.getcwd()
        server_cmd = f"cd {{current_dir}} && {{sys.executable}} -m uvicorn src.main:app --reload --port 8000"
        
        if sys.platform == 'darwin':
            osascript = f'tell application "Terminal" to do script "{{server_cmd}}"'
            subprocess.run(['osascript', '-e', osascript], check=True)
        
        print("\\nWeb project started!")
        print("Server running at: http://localhost:8000")
        
    elif type_name == "cli":
        print("\\nCLI project ready!")
        print(f"Run with: python -m {{name.lower().replace(' ', '_')}}")

if __name__ == '__main__':
    try:
        name, type_name, description = get_project_info()
        
        print("\\nGenerating project roadmap with AI...")
        roadmap = get_project_roadmap(name, type_name, description)
        
        print("\\nCreating project structure...")
        create_project_structure(roadmap, name, type_name)
        
        with open('project_roadmap.json', 'w') as f:
            json.dump(roadmap, f, indent=2)
        
        start_project(name, type_name)
        
        print("\\nOpening VS Code...")
        subprocess.run(['code', '.'], check=True)
        
    except KeyboardInterrupt:
        print("\\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\\nError: {{str(e)}}")
        sys.exit(1)
    '''
            
            # Save setup script
            setup_script_path = os.path.join(project_dir, '.setup_project.py')
            with open(setup_script_path, 'w') as f:
                f.write(setup_script)
            
            # Make script executable
            os.chmod(setup_script_path, 0o755)
            
            # Run setup script in new terminal
            command = f"cd {project_dir} && python {setup_script_path}"
            
            if self._is_iterm_available():
                osascript = (
                    'tell application "iTerm"\n'
                    '    create window with default profile\n'
                    '    tell current session of current window\n'
                    f'        write text "{command}"\n'
                    '    end tell\n'
                    'end tell'
                )
            else:
                osascript = f'tell application "Terminal" to do script "{command}"'
                
            subprocess.run(['osascript', '-e', osascript], check=True)
            print(f"\n{Fore.GREEN}Project setup started in new terminal window{ColoramaStyle.RESET_ALL}")
        
        except Exception as e:
            print(f"{Fore.RED}Error creating project: {str(e)}{ColoramaStyle.RESET_ALL}")


    def _is_iterm_available(self) -> bool:
        """Check if iTerm is installed and running."""
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "iTerm" to version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

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
    '''