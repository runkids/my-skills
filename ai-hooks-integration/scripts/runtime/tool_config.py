"""Centralized tool configuration for AI hooks integration.

This module provides a single source of truth for tool-specific configuration,
avoiding duplication across merge_hooks.py, remove_hooks.py, and other scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class ToolConfig(TypedDict, total=False):
    """Configuration for a single tool."""

    hook_key: str  # Key in hooks object (e.g., "PreToolUse")
    default_matcher: str | None  # Default matcher pattern
    nested: bool  # True = hooks[].hooks[], False = hooks[].command
    version: int  # Config version (Cursor only)
    config_path: str  # Default config file path
    plugin_template: str  # OpenCode only


# Centralized tool configuration
TOOL_CONFIG: dict[str, ToolConfig] = {
    "claude": {
        "hook_key": "PreToolUse",
        "default_matcher": "Bash",
        "nested": True,
        "config_path": "~/.claude/settings.json",
    },
    "gemini": {
        "hook_key": "BeforeTool",
        "default_matcher": "run_shell_command",
        "nested": True,
        "config_path": "~/.gemini/settings.json",
    },
    "cursor": {
        "hook_key": "beforeShellExecution",
        "default_matcher": None,
        "nested": False,
        "version": 1,
        "config_path": "~/.cursor/hooks.json",
    },
    "opencode": {
        "plugin_template": "opencode_plugin",
        "config_path": "~/.config/opencode/plugins",
    },
}

# Tools that support JSON-based hooks (not OpenCode)
JSON_TOOLS = ["claude", "gemini", "cursor"]


def get_config(tool: str) -> ToolConfig:
    """Get configuration for a tool.

    Args:
        tool: Tool name (claude, gemini, cursor, opencode).

    Returns:
        Tool configuration dict.

    Raises:
        KeyError: If tool is not supported.
    """
    if tool not in TOOL_CONFIG:
        raise KeyError(f"Unknown tool: {tool}. Supported: {list(TOOL_CONFIG.keys())}")
    return TOOL_CONFIG[tool]


def get_default_path(tool: str) -> Path:
    """Get default config path for a tool.

    Args:
        tool: Tool name.

    Returns:
        Expanded Path to config file/directory.
    """
    cfg = get_config(tool)
    return Path(cfg.get("config_path", "")).expanduser()


def is_nested(tool: str) -> bool:
    """Check if tool uses nested hook structure.

    Args:
        tool: Tool name.

    Returns:
        True if hooks use nested structure (hooks[].hooks[]).
    """
    return get_config(tool).get("nested", False)


# JSON utilities
def load_json(path: Path) -> dict:
    """Load JSON file, returning empty dict if not exists."""
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict, dry_run: bool = False) -> None:
    """Save JSON file with pretty formatting."""
    if dry_run:
        print(f"[dry-run] write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def has_hook(hooks: list, nested: bool, command: str) -> bool:
    """Check if a hook with the given command already exists.

    Args:
        hooks: List of hook entries.
        nested: Whether hooks use nested structure.
        command: Command string to search for (partial match).

    Returns:
        True if command is found in any hook entry.
    """
    if not isinstance(hooks, list):
        return False
    for h in hooks:
        if nested:
            inner = h.get("hooks", []) if isinstance(h, dict) else []
            for ih in inner:
                cmd = ih.get("command", "") if isinstance(ih, dict) else ""
                if command in cmd:
                    return True
        else:
            cmd = h.get("command", "") if isinstance(h, dict) else ""
            if command in cmd:
                return True
    return False
