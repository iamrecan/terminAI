# Terminal Agent

A powerful terminal-based assistant that integrates with various services including voice recognition, calendar management, and AI assistance.

## Features

- Voice Recognition and Text-to-Speech
- Calendar Integration (Apple Calendar)
- Notion Integration
- AI Assistant (Google AI)
- VS Code Integration
- Project Management Tools

## Project Structure

```
terminal_agent/
├── config/               # Configuration files
│   ├── .env             # Environment variables
│   └── .env.example     # Example environment variables
├── docs/                # Documentation
├── src/                 # Source code
│   └── terminal_agent/
│       ├── core/        # Core functionality
│       │   └── agent.py # Main agent implementation
│       ├── integrations/ # Third-party service integrations
│       │   ├── ai_integration.py
│       │   ├── apple_calendar_integration.py
│       │   ├── elevenlabs_integration.py
│       │   ├── notion_integration.py
│       │   ├── voice_integration.py
│       │   └── vscode_integration.py
│       └── utils/       # Utility functions and helpers
│           └── project_manager.py
├── tests/              # Test files
├── requirements.txt    # Project dependencies
└── setup.py           # Package setup file
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API keys
4. Run the agent:
   ```bash
   python src/terminal_agent/core/agent.py
   ```

## Configuration

The following environment variables are required:

- `NOTION_API_KEY`: Your Notion API key
- `GOOGLE_API_KEY`: Your Google AI API key
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key

## Usage

Type `help` in the terminal to see available commands:

- `time` - Show current time
- `events` - Show today's calendar events
- `tasks` - Show today's tasks from Notion
- `listen` - Start voice recognition
- `speak` - Convert text to speech
- `ask` - Ask the AI assistant a question
- `chat` - Start an interactive chat with AI
- `create-event` - Create a new calendar event

## Development

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## TODO

- [x] Add voice recognition
- [x] Add speech synthesis
- [x] Add ElevenLabs integration
- [x] Add Google AI integration
- [ ] Add project setup
- [ ] Add listen mode issue
- [ ] open vscode - Open VS Code will be replaced with a native VS Code integration
- [ ] conversation mode model has a bug firstly  change lanugage to english and then try to stop the conversation.
- [ ] run mode should to be improved
- [ ] project manager agent should to be improved
