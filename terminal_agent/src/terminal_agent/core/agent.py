#!/usr/bin/env python3
"""terminAI — main agent loop."""

import asyncio
import datetime
import json
import os
import subprocess
import sys
import threading
import time

from colorama import Fore, Style as ColoramaStyle, init
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from .config import config
from .command_registry import CommandRegistry
from .providers import LLMRouter
from ..integrations.calendars import CalendarProviderFactory
from ..memory import MemoryFactory

init()  # colorama


class TerminalAgent:
    def __init__(self):
        self.session = PromptSession()
        self.running = True
        self.conversation_thread = None

        self.style = Style.from_dict({"prompt": "#00aa00 bold"})

        # Core services
        self.llm = LLMRouter()
        self.registry = CommandRegistry()

        # Integrations (all optional — missing packages won't crash startup)
        self.notion = self._init_notion()
        self.calendar = self._init_calendar()
        self.voice = self._init_voice()
        self.vscode = self._init_vscode()
        self.aider = self._init_aider()
        self.project_manager = self._init_project_manager()
        self.memory = self._init_memory()
        self.composer = None

        self._register_commands()

    # ------------------------------------------------------------------ #
    # Init helpers                                                         #
    # ------------------------------------------------------------------ #

    def _init_notion(self):
        if not config.is_notion_enabled():
            return None
        try:
            from ..integrations.notion_integration import NotionIntegration
            return NotionIntegration()
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Notion not available — {e}{ColoramaStyle.RESET_ALL}")
            return None

    def _init_calendar(self):
        provider = CalendarProviderFactory.get_available_provider()
        if provider is None:
            print(f"{Fore.YELLOW}Warning: No calendar provider available{ColoramaStyle.RESET_ALL}")
        return provider

    def _init_voice(self):
        try:
            from ..integrations.voice_integration import VoiceAssistant
            return VoiceAssistant(llm_router=self.llm)
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else str(e)
            print(f"{Fore.YELLOW}Voice disabled — missing package: {missing}{ColoramaStyle.RESET_ALL}")
            print(f"{Fore.YELLOW}  Install: pip install pygame SpeechRecognition openai-whisper pyaudio{ColoramaStyle.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Voice not available — {e}{ColoramaStyle.RESET_ALL}")
            return None

    def _init_vscode(self):
        try:
            from ..integrations.vscode_integration import VSCodeIntegration
            return VSCodeIntegration()
        except Exception:
            return None

    def _init_aider(self):
        try:
            from ..integrations.aider_integration import AiderIntegration
            return AiderIntegration()
        except Exception:
            return None

    def _init_project_manager(self):
        try:
            from ..utils.project_manager import ProjectManager
            return ProjectManager()
        except Exception:
            return None

    def _init_memory(self):
        if not config.memory_enabled:
            return None
        try:
            from pathlib import Path
            db_path = Path(config.memory_db_path) if config.memory_db_path else None
            return MemoryFactory.create(backend=config.memory_backend, db_path=db_path)
        except Exception as e:
            print(f"{Fore.YELLOW}Memory disabled — {e}{ColoramaStyle.RESET_ALL}")
            return None

    # ------------------------------------------------------------------ #
    # Command registration                                                 #
    # ------------------------------------------------------------------ #

    def _register_commands(self):
        r = self.registry

        # system
        r.register("help",  self.show_help,  "Show available commands",       "system")
        r.register("exit",  self.cmd_exit,   "Exit terminAI",                 "system", aliases=["quit"])
        r.register("time",  self.cmd_time,   "Show current time",             "system")
        r.register("echo",  self.cmd_echo,   "Echo back your message",        "system")
        r.register("status", self.cmd_status, "Show provider status",         "system")

        # productivity
        r.register("tasks",        self.cmd_tasks,        "Show today's Notion tasks",             "productivity")
        r.register("events",       self.cmd_events,       "Show today's calendar events",          "productivity")
        r.register("agenda",       self.cmd_agenda,       "Show combined tasks and events",        "productivity")
        r.register("create-event", self.cmd_create_event, "Create a calendar event",               "productivity")

        # ai
        r.register("ask",  self.cmd_ask,  "Ask a one-time question to AI",        "ai")
        r.register("chat", self.cmd_chat, "Start an interactive chat with AI",     "ai")

        # voice
        r.register("listen",       self.cmd_listen,       "Start voice recognition",       "voice")
        r.register("speak",        self.cmd_speak,        "Convert text to speech",        "voice")
        r.register("stop",         self.cmd_stop,         "Stop voice recognition",        "voice")
        r.register("conversation", self.cmd_conversation, "Start voice conversation mode", "voice")
        r.register("stop conversation", self.cmd_stop_conversation, "Stop conversation",   "voice")

        # dev
        r.register("open vscode",   self.cmd_open_vscode,   "Open VS Code",                         "dev")
        r.register("terminal",      self.cmd_terminal,      "Open terminal in VS Code",              "dev")
        r.register("run",           self.cmd_run,           "Execute a shell command",               "dev")
        r.register("project",       self.cmd_project_help,  "Project setup help",                    "dev")
        r.register("aider",         self.cmd_aider,         "Start Aider AI coding assistant",       "dev")
        r.register("aider-status",  self.cmd_aider_status,  "Show AI coding assistant status",       "dev")
        r.register("create-project",self.cmd_create_project,"Create a new project with AI",          "dev")

        # plugins (Sprint 2)
        r.register("plugin",      self.cmd_plugin,      "Manage plugins (list/install/enable/disable)", "plugins")
        r.register("connect mcp", self.cmd_connect_mcp, "Connect to an MCP server",                    "plugins")
        r.register("mcp-tools",   self.cmd_mcp_tools,   "List tools from connected MCP server",         "plugins")
        r.register("mcp-disconnect", self.cmd_mcp_disconnect, "Disconnect from MCP server",             "plugins")

        # memory (Sprint 3)
        r.register("memory", self.cmd_memory, "Manage memory (show/search/clear)", "memory")

    # ------------------------------------------------------------------ #
    # System commands                                                      #
    # ------------------------------------------------------------------ #

    def show_help(self, *args):
        category_filter = args[0] if args else None
        categories = self.registry.categories()
        print(f"\n{Fore.GREEN}terminAI Commands:{ColoramaStyle.RESET_ALL}")
        for cat in categories:
            if category_filter and cat != category_filter:
                continue
            cmds = self.registry.list_commands(cat)
            print(f"\n  {Fore.CYAN}[{cat}]{ColoramaStyle.RESET_ALL}")
            for cmd in cmds:
                aliases = f"  (also: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                print(f"    {cmd.name:<20} {cmd.description}{aliases}")

    def cmd_exit(self, *args):
        self.running = False
        print(f"{Fore.YELLOW}Goodbye!{ColoramaStyle.RESET_ALL}")

    def cmd_time(self, *args):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Fore.GREEN}Current time: {now}{ColoramaStyle.RESET_ALL}")

    def cmd_echo(self, *args):
        print(f"{Fore.CYAN}{' '.join(args)}{ColoramaStyle.RESET_ALL}")

    def cmd_status(self, *args):
        print(f"\n{Fore.GREEN}LLM Providers:{ColoramaStyle.RESET_ALL}")
        for name, avail in self.llm.status().items():
            icon = f"{Fore.GREEN}✓" if avail else f"{Fore.RED}✗"
            print(f"  {icon} {name}{ColoramaStyle.RESET_ALL}")
        cal_name = self.calendar.name if self.calendar else "none"
        print(f"\n{Fore.GREEN}Calendar:{ColoramaStyle.RESET_ALL} {cal_name}")
        notion_status = "enabled" if self.notion else "disabled (no credentials)"
        print(f"{Fore.GREEN}Notion:{ColoramaStyle.RESET_ALL}  {notion_status}")
        voice_status = "enabled" if self.voice else "disabled"
        print(f"{Fore.GREEN}Voice:{ColoramaStyle.RESET_ALL}   {voice_status}")
        if self.memory:
            backend = type(self.memory).__name__
            print(f"{Fore.GREEN}Memory:{ColoramaStyle.RESET_ALL}  {backend} (enabled)")
        else:
            print(f"{Fore.GREEN}Memory:{ColoramaStyle.RESET_ALL}  disabled")

    # ------------------------------------------------------------------ #
    # Productivity commands                                                #
    # ------------------------------------------------------------------ #

    def cmd_tasks(self, *args):
        if not self.notion:
            print(f"{Fore.RED}Notion not configured — add NOTION_TOKEN and NOTION_DATABASE_ID to .env{ColoramaStyle.RESET_ALL}")
            return
        print(f"{Fore.CYAN}Today's Notion Tasks:{ColoramaStyle.RESET_ALL}")
        print(self.notion.get_tasks_for_today())

    def cmd_events(self, *args):
        if not self.calendar:
            print(f"{Fore.RED}No calendar provider available{ColoramaStyle.RESET_ALL}")
            return
        events = self.calendar.get_today_events()
        if not events:
            print(f"{Fore.YELLOW}No events scheduled for today{ColoramaStyle.RESET_ALL}")
            return
        print(f"\n{Fore.GREEN}Today's Schedule:{ColoramaStyle.RESET_ALL}")
        now = datetime.datetime.now()
        for ev in events:
            start_str = ev.start.strftime("%H:%M")
            end_str = ev.end.strftime("%H:%M")
            loc = f" @ {ev.location}" if ev.location else ""
            if ev.event_type == "reminder":
                status = "[✓]" if ev.completed else "[pending]"
                priority_str = "❗" * ev.priority
                overdue = " (OVERDUE)" if ev.start < now and not ev.completed else ""
                color = Fore.GREEN if ev.completed else (Fore.RED if overdue else "")
                print(f"{color}{start_str}: {status} {ev.title} {priority_str}{overdue}{ColoramaStyle.RESET_ALL}")
            else:
                if ev.start <= now <= ev.end:
                    print(f"{Fore.GREEN}[NOW] {start_str}-{end_str}: {ev.title}{loc}{ColoramaStyle.RESET_ALL}")
                else:
                    print(f"  {start_str}-{end_str}: {ev.title}{loc}")

    def cmd_agenda(self, *args):
        if self.notion:
            print(f"\n{Fore.BLUE}Notion Tasks:{ColoramaStyle.RESET_ALL}")
            self.cmd_tasks()
        if self.calendar:
            print(f"\n{Fore.GREEN}Calendar Events:{ColoramaStyle.RESET_ALL}")
            self.cmd_events()

    def cmd_create_event(self, *args):
        if not self.calendar:
            print(f"{Fore.RED}No calendar provider available{ColoramaStyle.RESET_ALL}")
            return
        if not args:
            print(f"{Fore.YELLOW}Usage: create-event <natural language description>{ColoramaStyle.RESET_ALL}")
            print('  Example: create-event Meeting with John tomorrow at 2pm at Starbucks')
            return
        event_text = " ".join(args)
        self._resolve_event_with_ai(event_text)

    def _resolve_event_with_ai(self, user_input: str):
        prompt = f"""You are a calendar assistant. Parse this event request and extract event details.
Request: {user_input}
Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

Respond with ONLY a JSON object containing these exact fields:
{{
    "title": "clear event title",
    "start_time": "YYYY-MM-DD HH:mm",
    "duration_minutes": 60,
    "location": "",
    "description": ""
}}"""
        try:
            response_text = asyncio.run(
                self.llm.complete(prompt, task_type="event_parsing")
            )
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            event_info = json.loads(text)
        except Exception as e:
            print(f"{Fore.RED}AI parsing failed: {e}{ColoramaStyle.RESET_ALL}")
            return

        try:
            from ..integrations.calendars.base_calendar import CalendarEvent
            start = datetime.datetime.strptime(event_info["start_time"], "%Y-%m-%d %H:%M")
            duration = int(event_info.get("duration_minutes", 60))
            end = start + datetime.timedelta(minutes=duration)

            now = datetime.datetime.now()
            if start < now:
                print(f"{Fore.YELLOW}Start time is in the past. Options:{ColoramaStyle.RESET_ALL}")
                print("  1. Schedule anyway")
                print("  2. Schedule for tomorrow")
                print("  3. Cancel")
                choice = input("Choose (1-3): ").strip()
                if choice == "2":
                    start += datetime.timedelta(days=1)
                    end += datetime.timedelta(days=1)
                elif choice != "1":
                    return

            ev = CalendarEvent(
                title=event_info["title"],
                start=start,
                end=end,
                location=event_info.get("location", ""),
                description=event_info.get("description", ""),
            )
            success = self.calendar.create_event(ev)
            if success:
                print(f"\n{Fore.GREEN}Event created:{ColoramaStyle.RESET_ALL}")
                print(f"  Title:  {ev.title}")
                print(f"  Start:  {start.strftime('%Y-%m-%d %H:%M')}")
                print(f"  End:    {end.strftime('%Y-%m-%d %H:%M')}")
                if ev.location:
                    print(f"  Location: {ev.location}")
            else:
                print(f"{Fore.RED}Failed to create event{ColoramaStyle.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error creating event: {e}{ColoramaStyle.RESET_ALL}")

    # ------------------------------------------------------------------ #
    # AI commands                                                          #
    # ------------------------------------------------------------------ #

    def cmd_ask(self, *args):
        if not args:
            print(f"{Fore.YELLOW}Usage: ask <your question>{ColoramaStyle.RESET_ALL}")
            return
        question = " ".join(args)
        print(f"{Fore.CYAN}Thinking...{ColoramaStyle.RESET_ALL}")
        try:
            context = self._memory_context(question)
            prompt = f"{context}{question}" if context else question
            response = asyncio.run(
                self.llm.complete(prompt, task_type="deep_reasoning")
            )
            self._memory_save("user", question)
            self._memory_save("assistant", response)
            print(f"\n{Fore.GREEN}AI:{ColoramaStyle.RESET_ALL} {response}")
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{ColoramaStyle.RESET_ALL}")

    def cmd_chat(self, *args):
        from .providers import Message
        history: list[Message] = []
        print(f"\n{Fore.CYAN}Chat mode — type 'exit' to end{ColoramaStyle.RESET_ALL}")
        while True:
            try:
                user_input = input(f"{Fore.CYAN}You: {ColoramaStyle.RESET_ALL}").strip()
                if user_input.lower() in ("exit", "quit", "bye"):
                    print(f"{Fore.GREEN}Chat ended.{ColoramaStyle.RESET_ALL}")
                    break
                # Inject relevant past context as a system prefix on the first message
                if not history and self.memory:
                    ctx = self._memory_context(user_input)
                    if ctx:
                        history.append(Message(role="system", content=ctx.strip()))
                history.append(Message(role="user", content=user_input))
                response = asyncio.run(
                    self.llm.chat(history, task_type="deep_reasoning")
                )
                history.append(Message(role="assistant", content=response))
                self._memory_save("user", user_input)
                self._memory_save("assistant", response)
                print(f"{Fore.GREEN}AI: {response}{ColoramaStyle.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Chat interrupted.{ColoramaStyle.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{ColoramaStyle.RESET_ALL}")

    # ------------------------------------------------------------------ #
    # Voice commands                                                       #
    # ------------------------------------------------------------------ #

    def cmd_listen(self, *args):
        if not self.voice:
            print(f"{Fore.RED}Voice not available{ColoramaStyle.RESET_ALL}")
            return
        print(f"{Fore.CYAN}Listening... (say 'stop' to end){ColoramaStyle.RESET_ALL}")
        self.voice.start_listening()
        t = threading.Thread(target=self._voice_loop, daemon=True)
        t.start()
        try:
            while self.voice.listening:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.voice.stop_listening()

    def _voice_loop(self):
        while self.voice and self.voice.listening:
            text = self.voice.listen()
            if text:
                if text.lower() in ("stop", "exit", "quit"):
                    self.voice.stop_listening()
                    break
                print(f"\n{Fore.CYAN}You said: {text}{ColoramaStyle.RESET_ALL}")
                try:
                    response = asyncio.run(
                        self.llm.complete(text, task_type="quick_answer")
                    )
                    print(f"{Fore.GREEN}AI: {response}{ColoramaStyle.RESET_ALL}")
                    self.voice.speak(response)
                except Exception as e:
                    print(f"{Fore.RED}Error: {e}{ColoramaStyle.RESET_ALL}")

    def cmd_speak(self, *args):
        if not self.voice:
            print(f"{Fore.RED}Voice not available{ColoramaStyle.RESET_ALL}")
            return
        text = " ".join(args)
        if not text:
            print(f"{Fore.YELLOW}Usage: speak <text>{ColoramaStyle.RESET_ALL}")
            return
        self.voice.speak(text)

    def cmd_stop(self, *args):
        if self.voice:
            self.voice.stop_listening()

    def cmd_conversation(self, *args):
        if not self.voice:
            print(f"{Fore.RED}Voice not available{ColoramaStyle.RESET_ALL}")
            return
        if self.conversation_thread and self.conversation_thread.is_alive():
            print("Conversation already running")
            return
        self.voice._conv_history.clear()  # fresh context for each session
        self.conversation_thread = threading.Thread(
            target=self.voice.start_conversation, daemon=True
        )
        self.conversation_thread.start()

    def cmd_stop_conversation(self, *args):
        if self.voice:
            self.voice.conversation_active = False

    # ------------------------------------------------------------------ #
    # Dev commands                                                         #
    # ------------------------------------------------------------------ #

    def cmd_open_vscode(self, *args):
        if not self.vscode:
            print(f"{Fore.RED}VSCode integration not available{ColoramaStyle.RESET_ALL}")
            return
        path = args[0] if args else None
        self.vscode.open_vscode(path)

    def cmd_terminal(self, *args):
        if not self.vscode:
            print(f"{Fore.RED}VSCode integration not available{ColoramaStyle.RESET_ALL}")
            return
        directory = args[0] if args else None
        self.vscode.open_terminal(directory)

    def cmd_run(self, *args):
        if not args:
            print(f"{Fore.YELLOW}Usage: run <command>{ColoramaStyle.RESET_ALL}")
            return
        if not self.vscode:
            # fallback: run directly
            result = subprocess.run(" ".join(args), shell=True, capture_output=True, text=True)
            print(result.stdout or result.stderr)
            return
        result = self.vscode.execute_command(" ".join(args))
        if result["success"]:
            print(result["stdout"])
        else:
            print(f"{Fore.RED}{result['stderr']}{ColoramaStyle.RESET_ALL}")

    def cmd_project_help(self, *args):
        print(f"\n{Fore.GREEN}Project Help:{ColoramaStyle.RESET_ALL}")
        print("  create-project <description>   Create a new project with AI assistance")

    def cmd_aider(self, *args):
        if not self.aider:
            print(f"{Fore.RED}Aider integration not available{ColoramaStyle.RESET_ALL}")
            return
        assistant = "aider"
        git_dir = None
        parsed_args = []
        i = 0
        args_list = list(args)
        while i < len(args_list):
            arg = args_list[i]
            if arg.startswith("--assistant="):
                assistant = arg.split("=", 1)[1]
            elif arg.startswith("--dir="):
                git_dir = arg.split("=", 1)[1]
            elif arg == "--dir" and i + 1 < len(args_list):
                i += 1
                git_dir = args_list[i]
            elif arg == "--list":
                for a in self.aider.list_available_assistants():
                    print(f"  - {a}")
                return
            else:
                parsed_args.append(arg)
            i += 1
        if not git_dir:
            print(f"{Fore.GREEN}Usage: aider --dir <path> [--assistant=<name>]{ColoramaStyle.RESET_ALL}")
            print(f"Available: {', '.join(self.aider.list_available_assistants())}")
            return
        self.aider.start_assistant(assistant=assistant, git_dir=os.path.expanduser(git_dir), args=parsed_args)

    def cmd_aider_status(self, *args):
        if not self.aider:
            print(f"{Fore.RED}Aider integration not available{ColoramaStyle.RESET_ALL}")
            return
        print(f"\n{Fore.GREEN}AI Coding Assistants:{ColoramaStyle.RESET_ALL}")
        for name, avail in self.aider.get_assistant_status().items():
            icon = f"{Fore.GREEN}✓" if avail else f"{Fore.RED}✗"
            print(f"  {icon} {name}{ColoramaStyle.RESET_ALL}")

    def cmd_create_project(self, *args):
        if not args:
            print(f"{Fore.YELLOW}Usage: create-project <description>{ColoramaStyle.RESET_ALL}")
            return
        description = " ".join(args)
        project_name = description.split()[0].lower()
        project_dir = os.path.join(os.getcwd(), project_name)
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "tests"), exist_ok=True)
        with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
            f.write("flask\npython-dotenv\n")
        with open(os.path.join(project_dir, "README.md"), "w") as f:
            f.write(f"# {project_name}\n\n{description}\n")
        print(f"\n{Fore.GREEN}Created: {project_dir}/{ColoramaStyle.RESET_ALL}")
        print("  ├── src/")
        print("  ├── tests/")
        print("  ├── requirements.txt")
        print("  └── README.md")
        try:
            prompt = f"I created a new {description} project. Give me the next 5 setup steps as a numbered list with commands. Be concise."
            response = asyncio.run(
                self.llm.complete(prompt, task_type="quick_answer")
            )
            print(f"\n{Fore.GREEN}Next steps (AI):{ColoramaStyle.RESET_ALL}")
            print(response)
        except Exception:
            print(f"\n{Fore.GREEN}Next steps:{ColoramaStyle.RESET_ALL}")
            print(f"  1. cd {project_name}")
            print("  2. python -m venv venv && source venv/bin/activate")
            print("  3. pip install -r requirements.txt")

    # ------------------------------------------------------------------ #
    # Plugin command (Sprint 2)                                            #
    # ------------------------------------------------------------------ #

    def cmd_plugin(self, *args):
        from ..plugins.plugin_registry import PluginRegistry
        if not args:
            print(f"{Fore.YELLOW}Usage: plugin <list|install|enable|disable> [name]{ColoramaStyle.RESET_ALL}")
            return
        sub = args[0].lower()
        name = args[1] if len(args) > 1 else None

        if sub == "list":
            registry = PluginRegistry.instance()
            plugins = registry.list_plugins()
            if not plugins:
                print(f"{Fore.YELLOW}No plugins loaded.{ColoramaStyle.RESET_ALL}")
                return
            print(f"\n{Fore.GREEN}Installed plugins:{ColoramaStyle.RESET_ALL}")
            for p in plugins:
                status = f"{Fore.GREEN}enabled{ColoramaStyle.RESET_ALL}" if p.enabled else f"{Fore.RED}disabled{ColoramaStyle.RESET_ALL}"
                print(f"  {p.name:<20} v{p.version}  {status}  — {p.description}")

        elif sub == "install":
            if not name:
                print(f"{Fore.YELLOW}Usage: plugin install <package-name>{ColoramaStyle.RESET_ALL}")
                return
            print(f"Installing {name}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"{Fore.GREEN}Installed. Restart terminAI to load the plugin.{ColoramaStyle.RESET_ALL}")
            else:
                print(f"{Fore.RED}Install failed:\n{result.stderr}{ColoramaStyle.RESET_ALL}")

        elif sub == "enable":
            if not name:
                print(f"{Fore.YELLOW}Usage: plugin enable <name>{ColoramaStyle.RESET_ALL}")
                return
            PluginRegistry.instance().enable(name)

        elif sub == "disable":
            if not name:
                print(f"{Fore.YELLOW}Usage: plugin disable <name>{ColoramaStyle.RESET_ALL}")
                return
            PluginRegistry.instance().disable(name)

        else:
            print(f"{Fore.RED}Unknown subcommand: {sub}{ColoramaStyle.RESET_ALL}")

    # ------------------------------------------------------------------ #
    # Memory commands (Sprint 3)                                           #
    # ------------------------------------------------------------------ #

    def cmd_memory(self, *args):
        if not self.memory:
            print(f"{Fore.YELLOW}Memory is disabled. Set MEMORY_ENABLED=true in .env{ColoramaStyle.RESET_ALL}")
            return
        sub = args[0].lower() if args else "show"

        if sub == "show":
            limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
            entries = asyncio.run(
                self.memory.get_recent(limit=limit)
            )
            if not entries:
                print(f"{Fore.YELLOW}No memories stored yet.{ColoramaStyle.RESET_ALL}")
                return
            print(f"\n{Fore.GREEN}Recent memories ({len(entries)}):{ColoramaStyle.RESET_ALL}")
            for e in entries:
                ts = e.timestamp.strftime("%m-%d %H:%M")
                role_color = Fore.CYAN if e.role == "user" else Fore.GREEN
                snippet = e.content[:120].replace("\n", " ")
                print(f"  {Fore.YELLOW}{ts}{ColoramaStyle.RESET_ALL} {role_color}[{e.role}]{ColoramaStyle.RESET_ALL} {snippet}")

        elif sub == "search":
            if len(args) < 2:
                print(f"{Fore.YELLOW}Usage: memory search <query>{ColoramaStyle.RESET_ALL}")
                return
            query = " ".join(args[1:])
            results = asyncio.run(
                self.memory.search(query, limit=5)
            )
            if not results:
                print(f"{Fore.YELLOW}No matching memories.{ColoramaStyle.RESET_ALL}")
                return
            print(f"\n{Fore.GREEN}Matches for '{query}':{ColoramaStyle.RESET_ALL}")
            for e in results:
                ts = e.timestamp.strftime("%m-%d %H:%M")
                role_color = Fore.CYAN if e.role == "user" else Fore.GREEN
                snippet = e.content[:200].replace("\n", " ")
                print(f"  {Fore.YELLOW}{ts}{ColoramaStyle.RESET_ALL} {role_color}[{e.role}]{ColoramaStyle.RESET_ALL} {snippet}")

        elif sub == "clear":
            confirm = input(f"{Fore.RED}Clear ALL memories? (yes/no): {ColoramaStyle.RESET_ALL}").strip().lower()
            if confirm == "yes":
                asyncio.run(self.memory.clear())
                print(f"{Fore.GREEN}Memory cleared.{ColoramaStyle.RESET_ALL}")
            else:
                print("Cancelled.")

        else:
            print(f"{Fore.YELLOW}Usage: memory [show [n] | search <query> | clear]{ColoramaStyle.RESET_ALL}")

    def _memory_save(self, role: str, content: str) -> None:
        """Fire-and-forget memory save (sync wrapper)."""
        if not self.memory:
            return
        try:
            asyncio.run(
                self.memory.save(role, content)
            )
        except Exception:
            pass

    def _memory_context(self, query: str, limit: int = 3) -> str:
        """Return a compact past-context string to prepend to prompts."""
        if not self.memory:
            return ""
        try:
            entries = asyncio.run(
                self.memory.search(query, limit=limit)
            )
            if not entries:
                return ""
            lines = [f"[{e.role}]: {e.content[:200]}" for e in entries]
            return "Relevant past context:\n" + "\n".join(lines) + "\n\n"
        except Exception:
            return ""

    # ------------------------------------------------------------------ #
    # MCP commands                                                         #
    # ------------------------------------------------------------------ #

    def cmd_connect_mcp(self, *args):
        from ..plugins.mcp_bridge import get_mcp_bridge
        bridge = get_mcp_bridge()
        bridge._cmd_connect(*args)
        # Register newly discovered tool commands into the main registry
        for cmd_name, (handler, desc) in bridge._dynamic_commands.items():
            if not self.registry.has(cmd_name):
                self.registry.register(cmd_name, handler, desc, "mcp")

    def cmd_mcp_tools(self, *args):
        from ..plugins.mcp_bridge import get_mcp_bridge
        get_mcp_bridge()._cmd_list_tools(*args)

    def cmd_mcp_disconnect(self, *args):
        from ..plugins.mcp_bridge import get_mcp_bridge
        get_mcp_bridge()._cmd_disconnect(*args)

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    def process_command(self, command_input: str):
        if not command_input.strip():
            return
        parts = command_input.strip().split()
        # Try multi-word commands first (e.g. "stop conversation", "open vscode")
        for length in (3, 2, 1):
            key = " ".join(parts[:length]).lower()
            if self.registry.has(key):
                return self.registry.dispatch(key, parts[length:])
        print(f"{Fore.RED}Unknown command: {parts[0]}. Type 'help' for commands.{ColoramaStyle.RESET_ALL}")

    def run(self):
        # Load plugins at startup
        try:
            from ..plugins.plugin_loader import PluginLoader
            PluginLoader.discover_and_load()
        except Exception:
            pass

        print(f"{Fore.GREEN}terminAI ready. Type 'help' for commands.{ColoramaStyle.RESET_ALL}")
        providers = [n for n, a in self.llm.status().items() if a]
        if providers:
            print(f"{Fore.CYAN}Active LLM providers: {', '.join(providers)}{ColoramaStyle.RESET_ALL}")

        while self.running:
            try:
                user_input = self.session.prompt("terminai> ", style=self.style)
                self.process_command(user_input)
            except KeyboardInterrupt:
                continue
            except EOFError:
                self.cmd_exit()
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{ColoramaStyle.RESET_ALL}")
