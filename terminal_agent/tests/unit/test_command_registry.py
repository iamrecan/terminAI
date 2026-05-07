"""Unit tests for CommandRegistry."""
import pytest
from src.terminal_agent.core.command_registry import CommandRegistry


def test_register_and_dispatch():
    r = CommandRegistry()
    called_with = []
    r.register("hello", lambda *a: called_with.extend(a), "Say hello", "test")
    r.dispatch("hello", ["world"])
    assert called_with == ["world"]


def test_alias():
    r = CommandRegistry()
    r.register("exit", lambda: None, "Exit", "system", aliases=["quit"])
    assert r.has("quit")
    assert r.has("exit")


def test_unknown_command_returns_none():
    r = CommandRegistry()
    result = r.dispatch("nonexistent", [])
    assert result is None


def test_list_by_category():
    r = CommandRegistry()
    r.register("time",  lambda: None, "Show time",  "system")
    r.register("ask",   lambda: None, "Ask AI",     "ai")
    r.register("tasks", lambda: None, "Show tasks", "productivity")

    system_cmds = r.list_commands("system")
    assert all(c.category == "system" for c in system_cmds)
    assert len(r.list_commands("ai")) == 1


def test_categories():
    r = CommandRegistry()
    r.register("a", lambda: None, "", "alpha")
    r.register("b", lambda: None, "", "beta")
    assert set(r.categories()) == {"alpha", "beta"}
