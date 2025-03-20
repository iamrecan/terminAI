import os
import asyncio
import datetime
import json
from typing import Dict, List, Optional
from pathlib import Path
from terminal_agent.integrations.voice_integration import VoiceAssistant
from terminal_agent.integrations.notion_integration import NotionIntegration
from terminal_agent.integrations.elevenlabs_integration import ElevenLabsIntegration
from terminal_agent.integrations.goose_integration import GooseIntegration
from terminal_agent.integrations.mcp_integration import MCPIntegration
from dotenv import load_dotenv
from colorama import Fore, Style

# Load environment variables
load_dotenv()

class ProjectManager:
    def __init__(self):
        """Initialize project manager."""
        self.goose = GooseIntegration()
        
        # Initialize MCP with API key from environment
        mcp_api_key = os.getenv("MCP_API_KEY")
        if mcp_api_key:
            self.mcp = MCPIntegration(mcp_api_key)
            # Connect to MCP server
            self.mcp_server_script = os.getenv("MCP_SERVER_SCRIPT")
            if self.mcp_server_script:
                asyncio.create_task(self.connect_mcp())
            else:
                print(f"{Fore.YELLOW}Warning: MCP_SERVER_SCRIPT not found in environment. MCP features will be limited.{Style.RESET_ALL}")
        else:
            self.mcp = None
            print(f"{Fore.YELLOW}Warning: MCP_API_KEY not found in environment. MCP features will be disabled.{Style.RESET_ALL}")
            
        # Project templates
        self.templates = {
            "todo": {
                "structure": [
                    "src/",
                    "src/models/",
                    "src/routes/",
                    "src/static/",
                    "src/templates/",
                    "tests/",
                    "docs/"
                ],
                "requirements": [
                    "flask",
                    "flask-sqlalchemy",
                    "flask-migrate",
                    "python-dotenv",
                    "pytest"
                ],
                "tasks": [
                    ("Setup Database Models", "Create SQLAlchemy models for Todo items"),
                    ("Implement API Routes", "Create RESTful API endpoints for CRUD operations"),
                    ("Create Frontend Templates", "Design and implement HTML templates with Bootstrap"),
                    ("Add User Authentication", "Implement user registration and login system"),
                    ("Write Tests", "Create unit tests for models and API endpoints"),
                    ("Add Documentation", "Write API documentation and setup instructions")
                ]
            }
        }
            
    async def connect_mcp(self):
        """Connect to MCP server."""
        try:
            await self.mcp.connect_to_server(self.mcp_server_script)
            print("Connected to MCP server successfully!")
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")
        
    async def handle_command(self, command: str) -> None:
        """Handle user command."""
        # Split command into parts
        parts = command.split()
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "voice":
            print("Starting voice assistant... Say 'exit', 'quit', or 'bye' to end.")
            self.voice_assistant.start()
        elif cmd == "conversation":
            print("Starting conversation mode...")
            self.voice_assistant.start_conversation()
        elif cmd == "show":
            if len(args) > 0 and args[0] == "tasks":
                await self.show_tasks()
            elif len(args) > 0 and args[0] == "events":
                print("Google Calendar integration is temporarily disabled")
            else:
                print("Unknown show command. Available: tasks, events")
        elif cmd == "create":
            if len(args) > 0:
                if args[0] == "task":
                    await self.create_task()
                elif args[0] == "event":
                    print("Google Calendar integration is temporarily disabled")
                elif args[0] == "project":
                    project_name = " ".join(args[1:]) if len(args) > 1 else None
                    await self.create_project(project_name)
                else:
                    print("Unknown create command. Available: task, event, project")
            else:
                print("Missing create type. Available: task, event, project")
        elif cmd == "translate":
            await self.translate_text()
        elif cmd == "create-project":
            project_name = " ".join(args) if args else None
            await self.create_project(project_name)
        else:
            print(f"Unknown command: {command}")
            
    def show_tasks(self) -> None:
        """Show tasks from Notion."""
        try:
            tasks = self.notion.get_tasks_for_today()
            if not tasks:
                print("No tasks found for today!")
                return
                
            print("\nTasks for today:")
            for task in tasks:
                print(f"- {task['title']}")
                
        except Exception as e:
            print(f"Error getting tasks: {str(e)}")
            
    def create_task(self) -> None:
        """Create a new Notion task."""
        title = input("Task title: ")
        description = input("Task description: ")
        
        try:
            self.notion.create_task(title, description)
            print("Task created successfully!")
        except Exception as e:
            print(f"Error creating task: {str(e)}")
            
    def translate_text(self) -> None:
        """Translate text using ElevenLabs."""
        text = input("Enter text to translate: ")
        target_language = input("Enter target language code (e.g., fr, es, de): ")
        
        try:
            translated_text = self.elevenlabs.translate_text(text, target_language)
            print(f"Translated text: {translated_text}")
        except Exception as e:
            print(f"Error translating text: {str(e)}")
            
    async def create_project(self, name: str = None) -> None:
        """Create a new project with Goose CLI and MCP."""
        print(f"{Fore.GREEN}Welcome to Project Creation Wizard!{Style.RESET_ALL}")
        
        # Get project details
        if not name:
            name = input(f"{Fore.CYAN}Project name: {Style.RESET_ALL}")
            
        # Detect project type from name
        project_type = None
        if "todo" in name.lower():
            project_type = "todo"
            print(f"\n{Fore.GREEN}Detected project type: Todo App{Style.RESET_ALL}")
            print("This will create a Flask-based Todo application with the following features:")
            print("- User Authentication")
            print("- RESTful API")
            print("- SQLite Database")
            print("- Bootstrap UI")
            print("- Unit Tests")
            print("- API Documentation")
            
            proceed = input(f"\n{Fore.YELLOW}Would you like to proceed with this template? (y/n): {Style.RESET_ALL}").lower()
            if proceed != 'y':
                print("Project creation cancelled.")
                return
        
        path = input(f"\n{Fore.CYAN}Project path (optional, press Enter for current directory): {Style.RESET_ALL}").strip()
        description = input(f"{Fore.CYAN}Project description: {Style.RESET_ALL}")
        
        try:
            # Create project using Goose
            print(f"\n{Fore.GREEN}Creating project structure...{Style.RESET_ALL}")
            goose_result = self.goose.create_project(name, path if path else None)
            if not goose_result['success']:
                print(f"{Fore.RED}Failed to create project with Goose: {goose_result.get('error', 'Unknown error')}{Style.RESET_ALL}")
                return
                
            project_path = goose_result['path']
            print(f"{Fore.GREEN}Project '{name}' created successfully at {project_path}{Style.RESET_ALL}")
            
            # Create project structure based on template
            if project_type and project_type in self.templates:
                template = self.templates[project_type]
                
                # Create directories
                print(f"\n{Fore.GREEN}Creating directory structure...{Style.RESET_ALL}")
                for dir_path in template['structure']:
                    full_path = os.path.join(project_path, dir_path)
                    os.makedirs(full_path, exist_ok=True)
                    print(f"Created directory: {dir_path}")
                
                # Create requirements.txt
                print(f"\n{Fore.GREEN}Creating requirements.txt...{Style.RESET_ALL}")
                with open(os.path.join(project_path, 'requirements.txt'), 'w') as f:
                    f.write('\n'.join(template['requirements']))
                print("Requirements file created")
                
                # Create README.md
                print(f"\n{Fore.GREEN}Creating README.md...{Style.RESET_ALL}")
                with open(os.path.join(project_path, 'README.md'), 'w') as f:
                    f.write(f"# {name}\n\n{description}\n\n")
                    f.write("## Setup\n\n")
                    f.write("1. Create a virtual environment:\n   ```\n   python -m venv venv\n   source venv/bin/activate  # On Windows: venv\\Scripts\\activate\n   ```\n\n")
                    f.write("2. Install dependencies:\n   ```\n   pip install -r requirements.txt\n   ```\n\n")
                    f.write("3. Run the application:\n   ```\n   flask run\n   ```\n")
                print("README.md created")
            
            # Create project in MCP if available
            if self.mcp:
                try:
                    print(f"\n{Fore.GREEN}Creating project in MCP...{Style.RESET_ALL}")
                    mcp_result = await self.mcp.create_project(name, description)
                    if mcp_result:
                        print("Project created in MCP successfully!")
                        
                        # Add tasks from template
                        print(f"\n{Fore.GREEN}Adding tasks to MCP...{Style.RESET_ALL}")
                        tasks = template['tasks'] if project_type in self.templates else [
                            ("Setup project structure", "Create basic project structure and configuration files"),
                            ("Add documentation", "Create README and other documentation files"),
                            ("Setup version control", "Initialize git repository and create .gitignore"),
                            ("Setup development environment", "Configure development tools and dependencies")
                        ]
                        
                        for task_name, task_desc in tasks:
                            # Add to Goose
                            goose_task = self.goose.add_task(project_path, task_name, task_desc)
                            if goose_task['success']:
                                print(f"Added task to Goose: {task_name}")
                            
                            # Add to MCP
                            mcp_task = await self.mcp.create_task(
                                mcp_result['id'],
                                task_name,
                                task_desc,
                                priority="medium"
                            )
                            if mcp_task:
                                print(f"Added task to MCP: {task_name}")
                                
                        # Generate roadmap in MCP
                        print(f"\n{Fore.GREEN}Generating project roadmap in MCP...{Style.RESET_ALL}")
                        roadmap = await self.mcp.generate_project_roadmap(mcp_result['id'])
                        if roadmap:
                            print("Project roadmap generated in MCP!")
                    else:
                        print(f"{Fore.RED}Warning: Failed to create project in MCP{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Warning: Error with MCP integration: {str(e)}{Style.RESET_ALL}")
            
            print(f"\n{Fore.GREEN}Project setup complete!{Style.RESET_ALL}")
            print(f"\nNext steps:")
            print(f"1. cd {project_path}")
            print(f"2. python -m venv venv")
            print(f"3. source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
            print(f"4. pip install -r requirements.txt")
            print(f"5. flask run")
            
            if self.mcp:
                print("\nCheck MCP dashboard for project roadmap and task management.")
            
        except Exception as e:
            print(f"{Fore.RED}Error creating project: {str(e)}{Style.RESET_ALL}")
