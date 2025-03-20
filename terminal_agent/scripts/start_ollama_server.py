#!/usr/bin/env python3

import os
import sys
import asyncio

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.terminal_agent.integrations.ollama_server import OllamaServer

async def main():
    server = OllamaServer()
    await server.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Ollama server...")

if __name__ == "__main__":
    asyncio.run(main())
