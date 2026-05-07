from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class Solution:
    description: str
    commands: List[str]
    code_changes: Optional[Dict[str, str]] = None
    confidence: float = 0.0

class LLMHandler:
    def __init__(self):
        from ..core.providers import LLMRouter
        self._router = LLMRouter()
    
    def analyze_terminal_output(self, output: str) -> Solution:
        """Analyze terminal output and generate solution"""
        prompt = f"""Analyze this terminal output and provide a solution:

Terminal Output:
{output}

Please provide a solution in this JSON format:
{{
    "analysis": "Brief analysis of the issue",
    "solution": {{
        "description": "Detailed description of the solution",
        "commands": ["list", "of", "commands", "to", "run"],
        "code_changes": {{
            "file_path": "content to change"
        }},
        "confidence": 0.0 to 1.0
    }}
}}

Focus on:
1. Command syntax errors
2. Missing dependencies
3. Configuration issues
4. Permission problems
5. Path-related issues"""

        try:
            import asyncio
            response_text = asyncio.get_event_loop().run_until_complete(
                self._router.complete(prompt, task_type="deep_reasoning")
            )
            # Strip markdown code fences if present
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            solution_data = json.loads(text)

            return Solution(
                description=solution_data['solution']['description'],
                commands=solution_data['solution']['commands'],
                code_changes=solution_data['solution'].get('code_changes'),
                confidence=solution_data['solution']['confidence']
            )
        except Exception as e:
            return Solution(
                description=f"Failed to analyze output: {str(e)}",
                commands=[],
                confidence=0.0
            )
    
    def validate_solution(self, solution: Solution) -> bool:
        """Validate if the solution is safe to apply"""
        # Check confidence level
        if solution.confidence < 0.7:
            return False
        
        # Check for dangerous commands
        dangerous_commands = ['rm -rf', 'sudo', 'chmod', 'chown']
        for cmd in solution.commands:
            if any(dangerous in cmd.lower() for dangerous in dangerous_commands):
                return False
        
        return True
    
    def generate_fix_script(self, solution: Solution) -> str:
        """Generate a Python script to apply the solution"""
        script = """#!/usr/bin/env python3
import os
import subprocess
import sys

def apply_solution():
    print("Applying solution...")
    
    # Create backup of files that will be modified
    """
        
        if solution.code_changes:
            script += "    # Backup files\n"
            for file_path in solution.code_changes.keys():
                script += f"    if os.path.exists('{file_path}'):\n"
                script += f"        os.rename('{file_path}', '{file_path}.bak')\n"
            
            script += "\n    # Apply code changes\n"
            for file_path, content in solution.code_changes.items():
                script += f"    with open('{file_path}', 'w') as f:\n"
                script += f"        f.write('''{content}''')\n"
        
        script += "\n    # Run commands\n"
        for cmd in solution.commands:
            script += f"    try:\n"
            script += f"        subprocess.run('{cmd}', shell=True, check=True)\n"
            script += f"    except subprocess.CalledProcessError as e:\n"
            script += f"        print(f'Command failed: {e}')\n"
            script += f"        return False\n"
        
        script += """
    return True

if __name__ == '__main__':
    if apply_solution():
        print("Solution applied successfully!")
    else:
        print("Failed to apply solution")
        sys.exit(1)
"""
        
        return script
