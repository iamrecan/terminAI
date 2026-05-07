from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable
from ..base_plugin import BasePlugin


class CodingPlugin(BasePlugin):
    """Wraps Aider and Goose coding assistants."""

    name = "coding"
    version = "0.1.0"
    description = "AI coding assistants (Aider, Goose)"
    commands = ["aider", "goose", "aider-status"]

    def __init__(self):
        self._aider = None

    def setup(self) -> bool:
        try:
            from ...integrations.aider_integration import AiderIntegration
            self._aider = AiderIntegration()
            return True
        except Exception as e:
            print(f"Coding plugin setup failed: {e}")
            return False

    def get_commands(self) -> dict[str, tuple[Callable, str]]:
        return {
            "aider-plugin": (self._cmd_aider, "Launch Aider in a new terminal window"),
            "aider-status-plugin": (self._cmd_status, "Show available coding assistants"),
        }

    def _cmd_aider(self, *args):
        if not self._aider:
            print("Aider not available.")
            return
        git_dir = None
        assistant = "aider"
        extra = []
        i = 0
        args_list = list(args)
        while i < len(args_list):
            if args_list[i].startswith("--dir="):
                git_dir = args_list[i].split("=", 1)[1]
            elif args_list[i] == "--dir" and i + 1 < len(args_list):
                i += 1
                git_dir = args_list[i]
            elif args_list[i].startswith("--assistant="):
                assistant = args_list[i].split("=", 1)[1]
            else:
                extra.append(args_list[i])
            i += 1
        if not git_dir:
            print("Usage: aider-plugin --dir <path>")
            return
        self._aider.start_assistant(
            assistant=assistant,
            git_dir=os.path.expanduser(git_dir),
            args=extra,
        )

    def _cmd_status(self, *args):
        if not self._aider:
            print("Coding plugin not loaded.")
            return
        for name, avail in self._aider.get_assistant_status().items():
            icon = "✓" if avail else "✗"
            print(f"  {icon} {name}")
