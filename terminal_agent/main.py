#!/usr/bin/env python3
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

from terminal_agent.core.agent import TerminalAgent

def main():
    """Run the terminal agent."""
    try:
        agent = TerminalAgent()
        agent.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
