import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class TerminalMessage:
    type: str  # 'error', 'warning', 'info', 'success'
    message: str
    details: Optional[Dict] = None
    timestamp: Optional[str] = None

class TerminalOutputComposer:
    def __init__(self):
        self.messages: List[TerminalMessage] = []
    
    def parse_output(self, output: str) -> List[TerminalMessage]:
        """Parse terminal output and categorize messages"""
        # Clear previous messages
        self.messages = []
        
        # Split output into lines
        lines = output.strip().split('\n')
        
        for line in lines:
            # Parse errors
            if 'Error:' in line or 'ERROR:' in line:
                error_details = self._parse_error_message(line)
                self.messages.append(TerminalMessage(
                    type='error',
                    message=line,
                    details=error_details
                ))
            
            # Parse warnings
            elif 'WARNING:' in line or 'Warning:' in line:
                self.messages.append(TerminalMessage(
                    type='warning',
                    message=line
                ))
            
            # Parse API responses
            elif any(api_term in line.lower() for api_term in ['api', 'key', 'token']):
                api_details = self._parse_api_message(line)
                if api_details:
                    self.messages.append(TerminalMessage(
                        type='info',
                        message=line,
                        details=api_details
                    ))
            
            # Parse success messages
            elif any(success_term in line.lower() for success_term in ['success', 'completed', 'created']):
                self.messages.append(TerminalMessage(
                    type='success',
                    message=line
                ))
        
        return self.messages
    
    def _parse_error_message(self, error_line: str) -> Dict:
        """Parse error message to extract details"""
        details = {}
        
        # Parse API errors
        api_error_match = re.search(r'(\d{3})\s+(.*?)\s+\[(.*?)\]', error_line)
        if api_error_match:
            details['status_code'] = api_error_match.group(1)
            details['error_type'] = api_error_match.group(2)
            details['error_details'] = api_error_match.group(3)
        
        # Parse Python errors
        python_error_match = re.search(r'File \"(.*?)\", line (\d+)', error_line)
        if python_error_match:
            details['file'] = python_error_match.group(1)
            details['line'] = python_error_match.group(2)
        
        return details
    
    def _parse_api_message(self, line: str) -> Optional[Dict]:
        """Parse API related messages"""
        api_details = {}
        
        # Check for API key related messages
        if 'API_KEY' in line:
            api_details['type'] = 'api_key'
            if 'invalid' in line.lower():
                api_details['status'] = 'invalid'
            elif 'not found' in line.lower():
                api_details['status'] = 'missing'
            else:
                api_details['status'] = 'info'
        
        return api_details if api_details else None
    
    def get_summary(self) -> str:
        """Generate a human-readable summary of the terminal output"""
        summary = []
        
        # Group messages by type
        errors = [msg for msg in self.messages if msg.type == 'error']
        warnings = [msg for msg in self.messages if msg.type == 'warning']
        infos = [msg for msg in self.messages if msg.type == 'info']
        successes = [msg for msg in self.messages if msg.type == 'success']
        
        # Add errors
        if errors:
            summary.append("❌ Errors:")
            for error in errors:
                if error.details:
                    summary.append(f"  - {error.message}")
                    for key, value in error.details.items():
                        summary.append(f"    {key}: {value}")
                else:
                    summary.append(f"  - {error.message}")
        
        # Add warnings
        if warnings:
            summary.append("\n⚠️ Warnings:")
            for warning in warnings:
                summary.append(f"  - {warning.message}")
        
        # Add important info
        if infos:
            summary.append("\nℹ️ Important Information:")
            for info in infos:
                if info.details:
                    summary.append(f"  - {info.message}")
                    for key, value in info.details.items():
                        summary.append(f"    {key}: {value}")
                else:
                    summary.append(f"  - {info.message}")
        
        # Add successes
        if successes:
            summary.append("\n✅ Successes:")
            for success in successes:
                summary.append(f"  - {success.message}")
        
        # Add recommendations if there are errors or warnings
        if errors or warnings:
            summary.append("\n💡 Recommendations:")
            if any(msg.details and msg.details.get('type') == 'api_key' for msg in self.messages):
                summary.append("  - Please check your API key is valid and properly configured")
            if any('file' in (msg.details or {}) for msg in errors):
                summary.append("  - Review the error locations in your code")
        
        return '\n'.join(summary)
