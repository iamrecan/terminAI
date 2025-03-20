import asyncio
import aiohttp
import json
from typing import Dict, List, Optional
from aiohttp import web

class OllamaServer:
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.ollama_url = "http://localhost:11434"
        self.available_models = []
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        self.app.router.add_get("/models", self.get_models)
        self.app.router.add_post("/generate", self.generate)
        self.app.router.add_post("/chat", self.chat)
        
    async def get_models(self, request: web.Request) -> web.Response:
        """Get list of available models from Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        models = await response.json()
                        return web.json_response(models)
                    else:
                        return web.json_response(
                            {"error": "Failed to get models from Ollama"},
                            status=500
                        )
        except Exception as e:
            return web.json_response(
                {"error": f"Error connecting to Ollama: {str(e)}"},
                status=500
            )
    
    async def generate(self, request: web.Request) -> web.Response:
        """Generate text using specified model"""
        try:
            data = await request.json()
            model = data.get("model", "codellama")
            prompt = data.get("prompt")
            stream = data.get("stream", False)
            
            if not prompt:
                return web.json_response(
                    {"error": "Prompt is required"},
                    status=400
                )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": stream
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return web.json_response(result)
                    else:
                        return web.json_response(
                            {"error": f"Ollama API error: {response.status}"},
                            status=response.status
                        )
        except Exception as e:
            return web.json_response(
                {"error": f"Error processing request: {str(e)}"},
                status=500
            )
    
    async def chat(self, request: web.Request) -> web.Response:
        """Chat with specified model"""
        try:
            data = await request.json()
            model = data.get("model", "codellama")
            messages = data.get("messages", [])
            stream = data.get("stream", False)
            
            if not messages:
                return web.json_response(
                    {"error": "Messages are required"},
                    status=400
                )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": stream
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return web.json_response(result)
                    else:
                        return web.json_response(
                            {"error": f"Ollama API error: {response.status}"},
                            status=response.status
                        )
        except Exception as e:
            return web.json_response(
                {"error": f"Error processing request: {str(e)}"},
                status=500
            )
    
    async def start(self):
        """Start the Ollama server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        
        print(f"Starting Ollama server on http://{self.host}:{self.port}")
        await site.start()

def main():
    server = OllamaServer()
    
    async def run_server():
        await server.start()
        while True:
            await asyncio.sleep(1)
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_server())
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
