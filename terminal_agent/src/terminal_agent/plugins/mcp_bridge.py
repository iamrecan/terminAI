"""
MCP Plugin Bridge.

Connects to any MCP server, discovers its tools, and registers each tool
as a terminAI command automatically.

Usage (inside the agent):
  > connect mcp http://localhost:3000
  ✓ 5 commands loaded: gh-issue, gh-pr, gh-commit, ...

  > gh-issue list --repo terminAI
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import aiohttp
from colorama import Fore, Style as ColoramaStyle

from .base_plugin import BasePlugin
from .plugin_registry import PluginRegistry


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


class MCPBridgePlugin(BasePlugin):
    """Dynamically wraps any MCP server as a terminAI plugin."""

    name = "mcp-bridge"
    version = "0.1.0"
    description = "Connect any MCP server as terminAI commands"
    commands = ["connect mcp", "mcp-disconnect", "mcp-tools"]

    def __init__(self, server_url: Optional[str] = None):
        self._server_url: Optional[str] = server_url
        self._tools: list[MCPTool] = []
        self._dynamic_commands: dict[str, tuple[Callable, str]] = {}

    def setup(self) -> bool:
        return True  # Always loads; actual connection happens on "connect mcp"

    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        base = {
            "connect mcp": (self._cmd_connect, "Connect to an MCP server: connect mcp <url>"),
            "mcp-disconnect": (self._cmd_disconnect, "Disconnect from MCP server"),
            "mcp-tools": (self._cmd_list_tools, "List tools from connected MCP server"),
        }
        base.update(self._dynamic_commands)
        return base

    # ------------------------------------------------------------------ #
    # Commands                                                             #
    # ------------------------------------------------------------------ #

    def _cmd_connect(self, *args):
        if not args:
            print(f"{Fore.YELLOW}Usage: connect mcp <url>{ColoramaStyle.RESET_ALL}")
            return
        url = args[0]
        print(f"Connecting to MCP server at {url}...")
        try:
            tools = asyncio.get_event_loop().run_until_complete(self.discover_tools(url))
            self._server_url = url
            self._tools = tools
            self._register_tool_commands()
            print(f"{Fore.GREEN}✓ {len(tools)} commands loaded: {', '.join(t.name for t in tools)}{ColoramaStyle.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Connection failed: {e}{ColoramaStyle.RESET_ALL}")

    def _cmd_disconnect(self, *args):
        self._server_url = None
        self._tools = []
        self._dynamic_commands.clear()
        print("Disconnected from MCP server.")

    def _cmd_list_tools(self, *args):
        if not self._tools:
            print("No MCP server connected. Use: connect mcp <url>")
            return
        print(f"\n{Fore.GREEN}MCP Tools ({self._server_url}):{ColoramaStyle.RESET_ALL}")
        for tool in self._tools:
            print(f"  {tool.name:<25} {tool.description}")

    # ------------------------------------------------------------------ #
    # MCP protocol                                                         #
    # ------------------------------------------------------------------ #

    async def discover_tools(self, server_url: str) -> list[MCPTool]:
        """Call MCP server's tools/list endpoint."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
            async with session.post(
                server_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Server returned {resp.status}")
                data = await resp.json()
                tools_data = data.get("result", {}).get("tools", [])
                return [
                    MCPTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                    )
                    for t in tools_data
                ]

    async def invoke_tool(self, tool_name: str, params: dict) -> Any:
        """Call a specific MCP tool."""
        if not self._server_url:
            raise RuntimeError("Not connected to any MCP server.")
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": params},
            }
            async with session.post(
                self._server_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if "error" in data:
                    raise RuntimeError(data["error"].get("message", "Unknown MCP error"))
                content = data.get("result", {}).get("content", [])
                # Return first text content
                for item in content:
                    if item.get("type") == "text":
                        return item["text"]
                return json.dumps(data.get("result", {}))

    def _register_tool_commands(self):
        """Create a CLI command handler for each MCP tool."""
        self._dynamic_commands.clear()
        for tool in self._tools:
            tool_name = tool.name

            def make_handler(t: MCPTool):
                def handler(*args):
                    params = self._parse_tool_args(t, list(args))
                    try:
                        result = asyncio.get_event_loop().run_until_complete(
                            self.invoke_tool(t.name, params)
                        )
                        print(result)
                    except Exception as e:
                        print(f"{Fore.RED}MCP error: {e}{ColoramaStyle.RESET_ALL}")
                return handler

            self._dynamic_commands[tool_name] = (make_handler(tool), tool.description)

    def _parse_tool_args(self, tool: MCPTool, args: list[str]) -> dict:
        """Parse CLI args (--key value) into MCP params dict."""
        params: dict = {}
        i = 0
        while i < len(args):
            if args[i].startswith("--") and i + 1 < len(args):
                key = args[i][2:]
                params[key] = args[i + 1]
                i += 2
            else:
                i += 1
        return params


def get_mcp_bridge() -> MCPBridgePlugin:
    """Get or create the singleton MCP bridge plugin."""
    registry = PluginRegistry.instance()
    bridge = registry.get("mcp-bridge")
    if bridge is None:
        bridge = MCPBridgePlugin()
        registry.register(bridge)
    return bridge
