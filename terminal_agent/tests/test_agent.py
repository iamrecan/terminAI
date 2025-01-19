"""Tests for the Terminal Agent."""

import unittest
from unittest.mock import MagicMock, patch
from terminal_agent.core.agent import TerminalAgent

class TestTerminalAgent(unittest.TestCase):
    """Test cases for Terminal Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = TerminalAgent()
        
    def test_get_time(self):
        """Test get_time command."""
        result = self.agent.get_time()
        self.assertIsNone(result)  # Command just prints, doesn't return
        
    def test_echo(self):
        """Test echo command."""
        test_message = "Hello, World!"
        result = self.agent.echo(test_message)
        self.assertIsNone(result)  # Command just prints, doesn't return
        
    @patch('terminal_agent.integrations.notion_integration.NotionIntegration')
    def test_show_tasks(self, mock_notion):
        """Test show_tasks command."""
        mock_notion.get_tasks_for_today.return_value = ["Task 1", "Task 2"]
        result = self.agent.show_tasks()
        self.assertIsNone(result)  # Command just prints, doesn't return
        
    @patch('terminal_agent.integrations.apple_calendar_integration.AppleCalendarIntegration')
    def test_show_events(self, mock_calendar):
        """Test show_events command."""
        mock_events = [
            {
                "type": "event",
                "title": "Test Event",
                "start": "2025-01-19T14:00:00",
                "end": "2025-01-19T15:00:00",
                "location": "Test Location"
            }
        ]
        mock_calendar.get_today_events.return_value = mock_events
        result = self.agent.show_events()
        self.assertIsNone(result)  # Command just prints, doesn't return

if __name__ == '__main__':
    unittest.main()
