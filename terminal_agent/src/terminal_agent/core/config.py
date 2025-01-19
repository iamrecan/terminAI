"""Configuration management for Terminal Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Load environment variables from config/.env
env_path = PROJECT_ROOT / "config" / ".env"
load_dotenv(env_path)

# API Keys and Credentials
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Calendar Configuration
CALENDAR_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
CALENDAR_TOKEN_FILE = "token.json"

# Voice Configuration
DEFAULT_LANGUAGE = "en-US"
DEFAULT_VOICE = "en-US-Standard-C"

# Application Settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def validate_config():
    """Validate that all required configuration is present."""
    required_vars = {
        "NOTION_TOKEN": NOTION_TOKEN,
        "NOTION_DATABASE_ID": NOTION_DATABASE_ID,
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
        "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
    return True
