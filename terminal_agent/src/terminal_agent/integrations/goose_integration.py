import subprocess
import json
from typing import Dict, Optional, List, Union
import os
from pathlib import Path

class GooseIntegration:
    def __init__(self):
        """Initialize Goose integration"""
        self._check_goose_installation()
        
    def _check_goose_installation(self):
        """Check if Goose CLI is installed"""
        try:
            result = subprocess.run(['goose', '--version'], 
                                 capture_output=True, 
                                 text=True)
            if result.returncode != 0:
                raise Exception("Goose CLI not found. Please install it first: curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash")
        except FileNotFoundError:
            raise Exception("Goose CLI not found. Please install it first: curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash")
            
    def create_project(self, name: str, path: Optional[str] = None) -> Dict:
        """
        Create a new Goose project
        
        Args:
            name (str): Project name
            path (Optional[str]): Project path. If not provided, creates in current directory
            
        Returns:
            Dict: Project information
        """
        try:
            cmd = ['goose', 'new', name]
            if path:
                cmd.extend(['--path', path])
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to create project: {result.stderr}")
                
            project_path = path if path else os.path.join(os.getcwd(), name)
            return {
                'name': name,
                'path': project_path,
                'success': True
            }
            
        except Exception as e:
            print(f"Error creating project: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def add_task(self, project_path: str, name: str, description: str = "") -> Dict:
        """
        Add a new task to a Goose project
        
        Args:
            project_path (str): Path to the project
            name (str): Task name
            description (str): Task description
            
        Returns:
            Dict: Task information
        """
        try:
            cmd = ['goose', 'task', 'add', name]
            if description:
                cmd.extend(['--description', description])
                
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True,
                                 cwd=project_path)
                                 
            if result.returncode != 0:
                raise Exception(f"Failed to add task: {result.stderr}")
                
            return {
                'name': name,
                'description': description,
                'success': True
            }
            
        except Exception as e:
            print(f"Error adding task: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def list_tasks(self, project_path: str, status: Optional[str] = None) -> List[Dict]:
        """
        List tasks in a Goose project
        
        Args:
            project_path (str): Path to the project
            status (Optional[str]): Filter tasks by status (todo, in-progress, done)
            
        Returns:
            List[Dict]: List of tasks
        """
        try:
            cmd = ['goose', 'task', 'list', '--json']
            if status:
                cmd.extend(['--status', status])
                
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True,
                                 cwd=project_path)
                                 
            if result.returncode != 0:
                raise Exception(f"Failed to list tasks: {result.stderr}")
                
            return json.loads(result.stdout)
            
        except Exception as e:
            print(f"Error listing tasks: {str(e)}")
            return []
            
    def update_task(self, project_path: str, task_id: str, 
                    status: Optional[str] = None, 
                    description: Optional[str] = None) -> Dict:
        """
        Update a task in a Goose project
        
        Args:
            project_path (str): Path to the project
            task_id (str): Task ID to update
            status (Optional[str]): New task status
            description (Optional[str]): New task description
            
        Returns:
            Dict: Updated task information
        """
        try:
            cmd = ['goose', 'task', 'update', task_id]
            if status:
                cmd.extend(['--status', status])
            if description:
                cmd.extend(['--description', description])
                
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True,
                                 cwd=project_path)
                                 
            if result.returncode != 0:
                raise Exception(f"Failed to update task: {result.stderr}")
                
            return {
                'id': task_id,
                'status': status,
                'description': description,
                'success': True
            }
            
        except Exception as e:
            print(f"Error updating task: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def generate_report(self, project_path: str, 
                       format: str = 'markdown',
                       output_file: Optional[str] = None) -> Optional[str]:
        """
        Generate a project report
        
        Args:
            project_path (str): Path to the project
            format (str): Report format (markdown, html, pdf)
            output_file (Optional[str]): Output file path
            
        Returns:
            Optional[str]: Report content if output_file is not provided
        """
        try:
            cmd = ['goose', 'report', 'generate', f'--format={format}']
            if output_file:
                cmd.extend(['--output', output_file])
                
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True,
                                 cwd=project_path)
                                 
            if result.returncode != 0:
                raise Exception(f"Failed to generate report: {result.stderr}")
                
            return result.stdout if not output_file else None
            
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            return None