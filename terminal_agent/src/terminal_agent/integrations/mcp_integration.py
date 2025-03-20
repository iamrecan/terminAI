import asyncio
import aiohttp
import json
import subprocess
import sys
import os
from typing import Dict, List, Optional, Union
from .ollama_server import OllamaServer

class MCPIntegration:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize MCP integration with either Ollama (local) or external API
        
        Args:
            api_key (str, optional): External API key. If not provided, will use local Ollama
        """
        self.api_key = api_key
        self.use_ollama = api_key is None
        self.ollama_server = None
        self.ollama_url = "http://localhost:8080"  # Our server port
        self.model = "codellama"  # Default model
        
    async def start_ollama_server(self) -> bool:
        """Start the Ollama server if using local Ollama"""
        if not self.use_ollama:
            return True
            
        try:
            # Check if Ollama is installed and running
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode != 0:
                print("Warning: Ollama is not running or not installed")
                return False
                
            # Start our Ollama server
            self.ollama_server = OllamaServer()
            await self.ollama_server.start()
            return True
            
        except FileNotFoundError:
            print("Error: Ollama is not installed. Please install it from https://ollama.ai/download")
            return False
        except Exception as e:
            print(f"Error starting Ollama server: {str(e)}")
            return False

    async def check_server_connection(self) -> bool:
        """Check connection to our server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/models") as response:
                    if response.status == 200:
                        models = await response.json()
                        print(f"Available models: {', '.join(m['name'] for m in models)}")
                        return True
                    return False
        except:
            return False

    async def connect_to_server(self) -> bool:
        """Connect to either Ollama or external API server"""
        if self.use_ollama:
            # Start our server first
            server_started = await self.start_ollama_server()
            if not server_started:
                return False
                
            # Check connection
            is_connected = await self.check_server_connection()
            if not is_connected:
                print("Warning: Could not connect to Ollama server")
            return is_connected
        else:
            # Here you would implement external API connection check
            return self.api_key is not None

    async def create_project(self, name: str, description: str, template: Optional[str] = None) -> Dict:
        """Create a new project using either Ollama or external API"""
        if self.use_ollama:
            prompt = f"Create a new {description} project named {name}."
            if template:
                prompt += f" Use the {template} template."
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Use our server's endpoint
                    async with session.post(
                        f"{self.ollama_url}/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False
                        }
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return {
                                "success": True,
                                "content": result.get("response", ""),
                                "model": self.model
                            }
                        else:
                            error_data = await response.json()
                            return {
                                "success": False,
                                "error": error_data.get("error", f"Server error: {response.status}")
                            }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error connecting to server: {str(e)}"
                }
        else:
            # Implement external API call here
            pass
            
    async def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict:
        """Chat with the AI model"""
        if self.use_ollama:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.ollama_url}/chat",
                        json={
                            "model": model or self.model,
                            "messages": messages,
                            "stream": False
                        }
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return {
                                "success": True,
                                "content": result.get("response", ""),
                                "model": model or self.model
                            }
                        else:
                            error_data = await response.json()
                            return {
                                "success": False,
                                "error": error_data.get("error", f"Server error: {response.status}")
                            }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error connecting to server: {str(e)}"
                }
        else:
            # Implement external API call here
            pass
        """
        Create a new project using MCP
        
        Args:
            name (str): Project name
            description (str): Project description
            template (Optional[str]): Template to use for project creation
            
        Returns:
            Dict: Created project information
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "create_project",
                {
                    "name": name,
                    "description": description,
                    "template": template
                }
            )
            return response.result
        except Exception as e:
            print(f"Error creating project: {str(e)}")
            return {}
            
    async def get_project_tasks(self, project_id: str) -> List[Dict]:
        """
        Get tasks for a project
        
        Args:
            project_id (str): Project ID
            
        Returns:
            List[Dict]: List of project tasks
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "get_project_tasks",
                {"project_id": project_id}
            )
            return response.result
        except Exception as e:
            print(f"Error getting project tasks: {str(e)}")
            return []
            
    async def create_task(self, project_id: str, title: str, description: str, 
                         assignee: Optional[str] = None, due_date: Optional[str] = None,
                         priority: Optional[str] = None) -> Dict:
        """
        Create a new task in a project
        
        Args:
            project_id (str): Project ID
            title (str): Task title
            description (str): Task description
            assignee (Optional[str]): Task assignee
            due_date (Optional[str]): Task due date (ISO format)
            priority (Optional[str]): Task priority
            
        Returns:
            Dict: Created task information
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "create_task",
                {
                    "project_id": project_id,
                    "title": title,
                    "description": description,
                    "assignee": assignee,
                    "due_date": due_date,
                    "priority": priority
                }
            )
            return response.result
        except Exception as e:
            print(f"Error creating task: {str(e)}")
            return {}
            
    async def update_task(self, task_id: str, **kwargs) -> Dict:
        """
        Update an existing task
        
        Args:
            task_id (str): Task ID
            **kwargs: Task fields to update
            
        Returns:
            Dict: Updated task information
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "update_task",
                {"task_id": task_id, **kwargs}
            )
            return response.result
        except Exception as e:
            print(f"Error updating task: {str(e)}")
            return {}
            
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "delete_task",
                {"task_id": task_id}
            )
            return response.result.get("success", False)
        except Exception as e:
            print(f"Error deleting task: {str(e)}")
            return False
            
    async def generate_project_roadmap(self, project_id: str) -> Dict:
        """
        Generate a project roadmap using MCP's AI capabilities
        
        Args:
            project_id (str): Project ID
            
        Returns:
            Dict: Generated roadmap information
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server first.")

        try:
            response = await self.session.call_tool(
                "generate_roadmap",
                {"project_id": project_id}
            )
            return response.result
        except Exception as e:
            print(f"Error generating roadmap: {str(e)}")
            return {}
            
    async def close(self):
        """
        Close the MCP connection and clean up resources
        """
        if self.exit_stack:
            await self.exit_stack.aclose()
