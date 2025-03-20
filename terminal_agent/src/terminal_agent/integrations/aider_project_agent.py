#!/usr/bin/env python3

import os
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
#import openai
from dotenv import load_dotenv

@dataclass
class CheckPoint:
    id: str
    timestamp: float
    description: str
    files_changed: List[str]
    status: str  # 'completed', 'in_progress', 'failed'

class AiderProjectAgent:
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.checkpoints_file = os.path.join(project_dir, '.aider_checkpoints.json')
        self.checkpoints: List[CheckPoint] = []
        self._load_checkpoints()
        self._setup_openai()
        
    def _setup_openai(self):
        """Setup OpenAI configuration."""
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        openai.api_key = api_key
        
    def _load_checkpoints(self):
        """Load checkpoints from file."""
        if os.path.exists(self.checkpoints_file):
            with open(self.checkpoints_file, 'r') as f:
                data = json.load(f)
                self.checkpoints = [CheckPoint(**cp) for cp in data]
                
    def _save_checkpoints(self):
        """Save checkpoints to file."""
        with open(self.checkpoints_file, 'w') as f:
            json.dump([vars(cp) for cp in self.checkpoints], f, indent=2)
            
    def create_checkpoint(self, description: str, files_changed: List[str]) -> CheckPoint:
        """Create a new checkpoint."""
        checkpoint = CheckPoint(
            id=f"cp_{int(time.time())}",
            timestamp=time.time(),
            description=description,
            files_changed=files_changed,
            status='completed'
        )
        self.checkpoints.append(checkpoint)
        self._save_checkpoints()
        return checkpoint
        
    def analyze_project_structure(self) -> Dict:
        """Analyze current project structure using GPT-4."""
        try:
            # Get current project structure
            file_list = []
            for root, _, files in os.walk(self.project_dir):
                for file in files:
                    if not file.startswith('.') and not file.endswith('.pyc'):
                        rel_path = os.path.relpath(os.path.join(root, file), self.project_dir)
                        file_list.append(rel_path)
                        
            # Create prompt for GPT-4
            prompt = f"""Analyze this Python project structure and suggest improvements:

Current files:
{json.dumps(file_list, indent=2)}

Please provide:
1. Project organization analysis
2. Missing key files/directories
3. Suggested new features or improvements
4. Next steps for development

Format the response as JSON with these keys:
- analysis: string
- missing_files: list of strings
- suggested_features: list of strings
- next_steps: list of strings
"""
            
            # Get GPT-4 analysis
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Python project management expert."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error analyzing project: {str(e)}")
            return {}
            
    def create_file_structure(self, files: List[str]) -> None:
        """Create suggested file structure."""
        try:
            for file_path in files:
                full_path = os.path.join(self.project_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                if not os.path.exists(full_path):
                    # Get file content suggestion from GPT-4
                    prompt = f"""Create content for Python file: {file_path}

Please provide appropriate code including:
1. Imports
2. Class/function definitions
3. Docstrings
4. Basic implementation
5. TODO comments for future work

The file should be ready to use but marked with areas needing completion."""
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a Python developer creating initial file templates."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    with open(full_path, 'w') as f:
                        f.write(response.choices[0].message.content)
                        
            self.create_checkpoint(
                description="Created suggested file structure",
                files_changed=files
            )
            
        except Exception as e:
            print(f"Error creating file structure: {str(e)}")
            
    def get_development_status(self) -> Dict:
        """Get current development status and suggestions."""
        if not self.checkpoints:
            return {"status": "No checkpoints found"}
            
        last_checkpoint = self.checkpoints[-1]
        
        return {
            "last_checkpoint": {
                "id": last_checkpoint.id,
                "description": last_checkpoint.description,
                "timestamp": time.ctime(last_checkpoint.timestamp)
            },
            "total_checkpoints": len(self.checkpoints),
            "files_modified": last_checkpoint.files_changed
        }
        
    def suggest_next_steps(self) -> List[str]:
        """Suggest next development steps based on project state."""
        analysis = self.analyze_project_structure()
        return analysis.get('next_steps', [])
