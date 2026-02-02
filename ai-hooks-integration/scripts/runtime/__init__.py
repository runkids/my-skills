"""Runtime utilities for AI hooks integration.

This module provides runtime utilities for detecting the actual source
of hook invocations and filtering noise events.
"""

from .detect_source import detect_parent_source, get_process_cmdline
from .tool_config import (
    TOOL_CONFIG,
    JSON_TOOLS,
    get_config,
    get_default_path,
    is_nested,
    load_json,
    save_json,
    has_hook,
)

__all__ = [
    "detect_parent_source",
    "get_process_cmdline",
    "TOOL_CONFIG",
    "JSON_TOOLS",
    "get_config",
    "get_default_path",
    "is_nested",
    "load_json",
    "save_json",
    "has_hook",
]
