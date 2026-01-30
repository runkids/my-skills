#!/usr/bin/env python3
"""Parent process detection for accurate source identification.

Problem:
  Cursor and OpenCode read ~/.claude/settings.json, triggering Claude's hooks.
  This causes the source to be misidentified as "claude" when it's actually
  "cursor" or "opencode".

Solution:
  Walk the process tree (up to 8 levels) and search command lines for known
  tool signatures. Override the --source parameter based on detection.

Usage:
  from runtime.detect_source import detect_parent_source

  source = args.source or "claude"
  inferred = detect_parent_source()
  if inferred and inferred != source:
      source = inferred  # Override!
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Known tool signatures in command lines (lowercase)
TOOL_SIGNATURES = {
    "cursor": ["cursor", "/cursor/"],
    "opencode": ["opencode", "/opencode/"],
    "gemini": ["gemini", "/gemini/"],
    "windsurf": ["windsurf", "/windsurf/"],
    "zed": ["/zed/", "zed.app"],
}

# Maximum depth to traverse process tree
MAX_DEPTH = 8


def get_process_cmdline(pid: int) -> str:
    """Get the command line of a process by PID.

    Args:
        pid: Process ID to look up.

    Returns:
        Command line string, or empty string if not accessible.

    Platform support:
        - macOS/Linux: reads /proc/{pid}/cmdline or uses ps command
        - Windows: uses wmic (limited support)
    """
    # Try /proc first (Linux, some macOS configurations)
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        try:
            # /proc/*/cmdline uses null bytes as separators
            return proc_cmdline.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        except (PermissionError, OSError):
            pass

    # Fallback: use ps command (macOS/Linux)
    if sys.platform != "win32":
        try:
            import subprocess

            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    return ""


def get_parent_pid(pid: int) -> int | None:
    """Get the parent PID of a process.

    Args:
        pid: Process ID to look up parent for.

    Returns:
        Parent PID, or None if not accessible or at root.
    """
    # Try /proc first
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            stat_content = proc_stat.read_text()
            # Format: pid (comm) state ppid ...
            # comm can contain spaces and parentheses, so find last ')'
            last_paren = stat_content.rfind(")")
            if last_paren > 0:
                parts = stat_content[last_paren + 1 :].split()
                if len(parts) >= 2:
                    return int(parts[1])
        except (PermissionError, OSError, ValueError):
            pass

    # Fallback: use ps command
    if sys.platform != "win32":
        try:
            import subprocess

            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "ppid="],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                ppid = int(result.stdout.strip())
                # Return None for init/launchd (pid 0 or 1)
                return ppid if ppid > 1 else None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
            pass

    return None


def detect_parent_source(max_depth: int = MAX_DEPTH) -> str | None:
    """Detect the actual source tool by walking the process tree.

    Walks up the process tree looking for known tool signatures in command
    lines. This allows accurate source identification even when hooks are
    triggered through shared config files.

    Args:
        max_depth: Maximum number of parent processes to check (default: 8).

    Returns:
        Detected tool name ("cursor", "opencode", "gemini", "windsurf", "zed"),
        or None if no known tool is detected.

    Example:
        >>> source = args.source or "claude"
        >>> inferred = detect_parent_source()
        >>> if inferred:
        ...     source = inferred  # Override the claimed source
    """
    pid = os.getppid()

    for _ in range(max_depth):
        if pid is None or pid <= 1:
            break

        cmdline = get_process_cmdline(pid).lower()
        if not cmdline:
            break

        # Check each tool's signatures
        for tool, signatures in TOOL_SIGNATURES.items():
            for sig in signatures:
                if sig in cmdline:
                    return tool

        # Move to parent
        pid = get_parent_pid(pid)

    return None


def debug_process_tree(max_depth: int = MAX_DEPTH) -> list[dict]:
    """Get process tree info for debugging.

    Returns:
        List of dicts with 'pid', 'cmdline', and 'detected' keys.
    """
    result = []
    pid = os.getppid()

    for _ in range(max_depth):
        if pid is None or pid <= 1:
            break

        cmdline = get_process_cmdline(pid)
        cmdline_lower = cmdline.lower()

        detected = None
        for tool, signatures in TOOL_SIGNATURES.items():
            for sig in signatures:
                if sig in cmdline_lower:
                    detected = tool
                    break
            if detected:
                break

        result.append({"pid": pid, "cmdline": cmdline[:100], "detected": detected})

        pid = get_parent_pid(pid)

    return result


if __name__ == "__main__":
    # Debug mode: print process tree
    print("Process tree detection debug:")
    print(f"  Current PID: {os.getpid()}")
    print(f"  Parent PID: {os.getppid()}")
    print()

    tree = debug_process_tree()
    for i, proc in enumerate(tree):
        marker = " <--" if proc["detected"] else ""
        print(f"  [{i}] PID {proc['pid']}: {proc['cmdline'][:60]}...{marker}")
        if proc["detected"]:
            print(f"      Detected: {proc['detected']}")

    print()
    detected = detect_parent_source()
    print(f"Final detection: {detected or 'None (defaults to claude)'}")
