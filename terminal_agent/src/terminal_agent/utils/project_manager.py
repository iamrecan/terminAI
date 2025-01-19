import os
import json
import datetime
from typing import Dict, List, Optional
from pathlib import Path

from ..integrations.voice_integration import VoiceAssistant
from ..integrations.notion_integration import NotionIntegration
from ..integrations.elevenlabs_integration import ElevenLabsIntegration

class ProjectManager:
    def __init__(self):
        """Initialize project manager."""
        self.voice_assistant = VoiceAssistant()
        self.notion = NotionIntegration()
        self.elevenlabs = ElevenLabsIntegration()
        
    def handle_command(self, command: str) -> None:
        """Handle user command."""
        if command == "voice":
            print("Starting voice assistant... Say 'exit', 'quit', or 'bye' to end.")
            self.voice_assistant.start()
        elif command == "conversation":
            print("Starting conversation mode...")
            self.voice_assistant.start_conversation()
        elif command == "show tasks":
            self.show_tasks()
        elif command == "show events":
            # self.show_events()
            print("Google Calendar integration is temporarily disabled")
        elif command == "create event":
            # self.create_event()
            print("Google Calendar integration is temporarily disabled")
        elif command == "create task":
            self.create_task()
        elif command == "translate":
            self.translate_text()
        else:
            print(f"Unknown command: {command}")
            
    def show_tasks(self) -> None:
        """Show tasks from Notion."""
        tasks = self.notion.get_tasks()
        if tasks:
            print("\nTasks from Notion:")
            for task in tasks:
                print(f"- {task['title']}")
        else:
            print("No tasks found in Notion")
            
    def show_events(self) -> None:
        """Show events from Google Calendar."""
        print("Google Calendar integration is temporarily disabled")
            
    def create_event(self) -> None:
        """Create a new calendar event."""
        print("Google Calendar integration is temporarily disabled")
            
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
        text = input("Text to translate: ")
        language = input("Target language: ")
        
        try:
            translated_text = self.elevenlabs.translate_text(text, language)
            print(f"Translated text: {translated_text}")
        except Exception as e:
            print(f"Error translating text: {str(e)}")
