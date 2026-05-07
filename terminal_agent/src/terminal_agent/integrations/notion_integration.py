from notion_client import Client
from datetime import datetime
import os

class NotionIntegration:
    def __init__(self):
        from ..core.config import config
        self.notion = Client(auth=config.notion_token)
        self.database_id = config.notion_database_id

    def get_tasks_for_today(self):
        if not self.notion or not self.database_id:
            return "Notion credentials not configured. Please check your .env file."

        today = datetime.now().date()
        print(today)
        
        try:
            response = self.notion.databases.query(
                database_id=self.database_id,
                filter={
                    "and": [
                        {
                            "property": "Date",
                            "date": {
                                "equals": today.isoformat()
                            }
                        }
                    ]
                }
            )

            tasks = []
            for page in response["results"]:
                task_name = page["properties"].get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
                status = page["properties"].get("Status", {}).get("select", {}).get("name", "No Status")
                tasks.append(f"- {task_name} ({status})")

            return "\n".join(tasks) if tasks else "No tasks found for today in Notion"

        except Exception as e:
            return f"Error fetching Notion tasks: {str(e)}"
