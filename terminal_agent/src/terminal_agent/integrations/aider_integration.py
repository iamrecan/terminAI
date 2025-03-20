#!/usr/bin/env python3

import os
import subprocess
from dotenv import load_dotenv
from typing import Optional, Dict, List
from .aider_project_agent import AiderProjectAgent
import json
#import openai

class AiderIntegration:
    """Integration for Aider and other AI coding assistants."""
    
    def __init__(self):
        env_path = os.path.join(os.path.dirname(__file__), "../../../config/.env")
        load_dotenv(env_path)
        
        # Load API keys
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.gemini_key = os.getenv('GOOGLE_AI_KEY')
        
        # Initialize status flags
        self.available_assistants = self._check_available_assistants()
        self.project_agents: Dict[str, AiderProjectAgent] = {}
        
    def _check_available_assistants(self) -> Dict[str, bool]:
        """Check which AI assistants are available based on API keys."""
        return {
            'aider': bool(self.openai_key and self._is_command_available('aider')),
            'deepseek': bool(self.deepseek_key),
            'anthropic': bool(self.anthropic_key),
            'gemini': bool(self.gemini_key)
        }
        
    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
            
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
            
    def _get_env_for_assistant(self, assistant: str) -> Dict[str, str]:
        """Get environment variables for specific assistant."""
        env = os.environ.copy()
        
        if assistant == 'aider':
            if self.openai_key:
                env['OPENAI_API_KEY'] = self.openai_key
        elif assistant == 'deepseek':
            if self.deepseek_key:
                env['DEEPSEEK_API_KEY'] = self.deepseek_key
        elif assistant == 'anthropic':
            if self.anthropic_key:
                env['ANTHROPIC_API_KEY'] = self.anthropic_key
        elif assistant == 'gemini':
            if self.gemini_key:
                env['GOOGLE_AI_KEY'] = self.gemini_key
                
        return env
        
    def _get_project_roadmap(self, project_name: str, project_description: str) -> Dict:
        """Get project roadmap from GPT-4."""
        try:
            prompt = f"""Create a detailed roadmap for this Python project:

Project Name: {project_name}
Description: {project_description}

Please provide:
1. Project overview and goals
2. Technical architecture
3. Core features and components
4. Development phases
5. File structure
6. Dependencies
7. Testing strategy
8. Deployment considerations

Format the response as JSON with these keys:
- overview: string
- architecture: object with components and their descriptions
- features: list of objects with name, description, and priority
- phases: list of objects with phase name, tasks, and estimated duration
- file_structure: object with directories and files
- dependencies: list of required packages with versions
- testing: object with strategy and test types
- deployment: object with requirements and steps
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Python project architect and technical lead."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error getting project roadmap: {str(e)}")
            return {}
            
    def _initialize_project(self, project_dir: str, project_name: str, roadmap: Dict) -> bool:
        """Initialize a new project directory with roadmap."""
        try:
            # Create project directory if it doesn't exist
            os.makedirs(project_dir, exist_ok=True)
            
            # Initialize git if not already initialized
            git_dir = os.path.join(project_dir, '.git')
            if not os.path.exists(git_dir):
                subprocess.run(['git', 'init'], cwd=project_dir, check=True)
                
            # Create project structure from roadmap
            file_structure = roadmap.get('file_structure', {})
            dependencies = roadmap.get('dependencies', [])
            
            # Create README.md with project overview
            readme_content = f"""# {project_name}

{roadmap.get('overview', 'Add project description here.')}

## Architecture
{json.dumps(roadmap.get('architecture', {}), indent=2)}

## Features
{json.dumps(roadmap.get('features', []), indent=2)}

## Development Phases
{json.dumps(roadmap.get('phases', []), indent=2)}

## Getting Started
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `config/.env.example` to `config/.env` and set your API keys
4. Run the tests: `python -m pytest`
"""
            
            # Create basic files
            basic_files = {
                'README.md': readme_content,
                '.gitignore': '*.pyc\n__pycache__\n.env\n.aider*\n.vscode\n',
                'requirements.txt': '\n'.join(f"{dep}" for dep in dependencies),
                'setup.py': f'''from setuptools import setup, find_packages

setup(
    name="{project_name.lower().replace(' ', '_')}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
)''',
                'config/.env.example': 'OPENAI_API_KEY=your_key_here\nGOOGLE_AI_KEY=your_key_here\n',
                'tests/__init__.py': '',
            }
            
            # Add roadmap-specific files
            basic_files.update(file_structure)
            
            # Create all files
            for file_path, content in basic_files.items():
                full_path = os.path.join(project_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                if not os.path.exists(full_path):
                    with open(full_path, 'w') as f:
                        f.write(str(content))
                        
            # Copy .env if it doesn't exist
            env_example = os.path.join(project_dir, 'config/.env.example')
            env_file = os.path.join(project_dir, 'config/.env')
            if os.path.exists(env_example) and not os.path.exists(env_file):
                with open(env_example, 'r') as src, open(env_file, 'w') as dst:
                    dst.write(src.read())
                    
            # Save roadmap for future reference
            roadmap_file = os.path.join(project_dir, 'project_roadmap.json')
            with open(roadmap_file, 'w') as f:
                json.dump(roadmap, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error initializing project: {str(e)}")
            return False
            
    def _create_terminal_command(self, assistant: str, git_dir: Optional[str], args: List[str]) -> str:
        """Create the command to run in the new terminal."""
        if not git_dir:
            return f"echo 'Error: No directory specified'; read -p 'Press enter to exit...'"
            
        # Ensure directory exists
        os.makedirs(git_dir, exist_ok=True)
        cd_cmd = f"cd {git_dir}"
        
        if assistant == 'aider':
            # Get project info if new project
            if not os.path.exists(os.path.join(git_dir, '.git')):
                # Create interactive project setup script
                setup_script = f'''
import os
import json
from prompt_toolkit import prompt

def get_project_info():
    print("\\n=== New Project Setup ===\\n")
    project_name = prompt('Enter project name: ')
    print("\\nEnter project description (what will this project do?):")
    project_description = prompt('> ')
    return project_name, project_description

def save_project_info(name, description):
    with open('.project_info.json', 'w') as f:
        json.dump({{'name': name, 'description': description}}, f)
    print("\\nProject info saved! Initializing project structure...")

if __name__ == '__main__':
    try:
        name, desc = get_project_info()
        save_project_info(name, desc)
    except KeyboardInterrupt:
        print("\\nSetup cancelled.")
        exit(1)
    except Exception as e:
        print(f"\\nError: {{str(e)}}")
        exit(1)
'''
                setup_script_path = os.path.join(git_dir, '.setup_project.py')
                with open(setup_script_path, 'w') as f:
                    f.write(setup_script)
                    
                # Run setup and initialize project
                return f'''
{cd_cmd}
python {setup_script_path}
rm {setup_script_path}
code .
aider {' '.join(args) if args else ''}
'''
            
            # Project exists, just start aider
            return f"{cd_cmd}; aider {' '.join(args) if args else ''}"
            
        elif assistant == 'gemini':
            # Create a temporary Python script for Gemini interactive shell
            script_content = '''
import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys

def init_gemini():
    # Load environment variables from multiple possible locations
    env_paths = [
        os.path.join(os.getcwd(), 'config', '.env'),
        os.path.join(os.getcwd(), '.env'),
        os.path.expanduser('~/.env')
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break
    
    # Configure API
    api_key = os.getenv('GOOGLE_AI_KEY')
    if not api_key:
        print("Error: GOOGLE_AI_KEY not found in environment variables")
        print("Please set your Google AI API key in one of these locations:")
        for path in env_paths:
            print(f"- {path}")
        print("\\nFormat: GOOGLE_AI_KEY=your_api_key_here")
        return False
        
    try:
        genai.configure(api_key=api_key)
        # Test the configuration
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("test")
        return True
    except Exception as e:
        print(f"Error configuring Gemini: {str(e)}")
        return False

def main():
    print("Initializing Gemini interactive shell...")
    if not init_gemini():
        return
        
    # Create model and chat
    model = genai.GenerativeModel('gemini-pro')
    chat = model.start_chat(history=[])
    
    print("\\nGemini Interactive Shell")
    print("Type 'exit' to quit, 'clear' to start new chat")
    print("Enter your message:")
    
    while True:
        try:
            # Get input
            user_input = input("\\nYou: ").strip()
            
            # Check for commands
            if user_input.lower() == 'exit':
                print("\\nGoodbye!")
                break
            elif user_input.lower() == 'clear':
                chat = model.start_chat(history=[])
                print("\\nChat history cleared.")
                continue
            elif not user_input:
                continue
                
            # Get response
            response = chat.send_message(user_input)
            print(f"\\nGemini: {response.text}")
            
        except KeyboardInterrupt:
            print("\\nExiting...")
            break
        except Exception as e:
            print(f"\\nError: {str(e)}")

if __name__ == '__main__':
    main()
'''
            script_path = os.path.join(git_dir or os.getcwd(), '.gemini_shell.py')
            with open(script_path, 'w') as f:
                f.write(script_content)
            return f"{cd_cmd}; python {script_path}; rm {script_path}"
        else:
            return f"echo 'Error: {assistant} is not supported yet'; read -p 'Press enter to exit...'"
            
    def start_assistant(self, assistant: str = 'aider', git_dir: Optional[str] = None, args: List[str] = None) -> bool:
        """Start an AI coding assistant in a new terminal window."""
        if not self.available_assistants.get(assistant, False):
            print(f"Error: {assistant} is not available. Please check API key and installation.")
            return False
            
        try:
            env = self._get_env_for_assistant(assistant)
            command = self._create_terminal_command(assistant, git_dir, args)
            
            # Check if iTerm is available
            use_iterm = self._is_iterm_available()
            
            if use_iterm:
                # iTerm2 AppleScript command
                osascript_command = f'''
                    tell application "iTerm"
                        activate
                        tell current window
                            create tab with default profile
                            tell current session
                                write text "{command}"
                            end tell
                        end tell
                    end tell
                '''
            else:
                # Fallback to Terminal.app
                osascript_command = f'''
                    tell application "Terminal"
                        activate
                        tell application "System Events" to tell process "Terminal" to keystroke "t" using command down
                        delay 0.1
                        do script "{command}" in selected tab of the front window
                    end tell
                '''
            
            subprocess.run(['osascript', '-e', osascript_command], env=env, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error starting {assistant}: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False
            
    def list_available_assistants(self) -> List[str]:
        """List all available AI coding assistants."""
        return [name for name, available in self.available_assistants.items() if available]
        
    def get_assistant_status(self) -> Dict[str, bool]:
        """Get the status of all AI coding assistants."""
        return self.available_assistants.copy()