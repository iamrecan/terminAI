import subprocess
import os
import platform
import json
from typing import Optional, List, Dict

class VSCodeIntegration:
    def __init__(self):
        self.system = platform.system()
        if self.system == 'Darwin':  # macOS
            self.vscode_cmd = 'code'
        elif self.system == 'Windows':
            self.vscode_cmd = 'code.cmd'
        else:  # Linux
            self.vscode_cmd = 'code'
            
    def open_vscode(self, path: Optional[str] = None) -> bool:
        """
        Open VS Code, optionally with a specific file or directory
        """
        try:
            cmd = [self.vscode_cmd]
            if path:
                cmd.append(path)
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            print(f"Error opening VS Code: {e}")
            return False
            
    def open_terminal(self, directory: Optional[str] = None) -> bool:
        """
        Open a new terminal in VS Code
        """
        try:
            cmd = [self.vscode_cmd, '--new-window']
            if directory:
                cmd.extend(['--folder-uri', f'file://{directory}'])
            subprocess.Popen(cmd + ['--launch-profile', 'terminal'])
            return True
        except Exception as e:
            print(f"Error opening terminal: {e}")
            return False
            
    def execute_command(self, command: str, cwd: Optional[str] = None) -> Dict:
        """
        Execute a command in the terminal and return the result
        """
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True
            )
            stdout, stderr = process.communicate()
            return {
                'success': process.returncode == 0,
                'stdout': stdout,
                'stderr': stderr,
                'code': process.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'code': -1
            }
            
    def create_workspace(self, path: str, files: List[str] = None) -> bool:
        """
        Create a VS Code workspace with specified files
        """
        try:
            workspace = {
                'folders': [{'path': path}],
                'settings': {}
            }
            
            workspace_file = os.path.join(path, 'workspace.code-workspace')
            with open(workspace_file, 'w') as f:
                json.dump(workspace, f, indent=2)
                
            # Open workspace in VS Code
            self.open_vscode(workspace_file)
            
            # Open specified files if any
            if files:
                for file in files:
                    full_path = os.path.join(path, file)
                    if os.path.exists(full_path):
                        self.open_vscode(full_path)
                        
            return True
        except Exception as e:
            print(f"Error creating workspace: {e}")
            return False
            
    def install_extension(self, extension_id: str) -> bool:
        """
        Install a VS Code extension
        """
        try:
            result = self.execute_command(f'{self.vscode_cmd} --install-extension {extension_id}')
            return result['success']
        except Exception as e:
            print(f"Error installing extension: {e}")
            return False
