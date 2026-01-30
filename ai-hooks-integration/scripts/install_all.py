#!/usr/bin/env python3
"""Install the same hook command across Claude/Gemini/Cursor and write OpenCode plugin.

Usage:
  install_all.py --command "/abs/path/to/hook" --name my-hook

  # Unified mode (recommended): Uses unified_hook.py with automatic source detection
  install_all.py --unified --handler "/abs/path/to/handler" --name my-hook

Notes:
  - Adds tool-specific suffixes: --claude/--gemini/--cursor
  - Writes OpenCode plugin to ~/.config/opencode/plugins/<name>.js
  - Unified mode automatically detects the actual source tool and filters noise events
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MERGE = ROOT / "merge_hooks.py"
UNIFIED_HOOK = ROOT / "runtime" / "unified_hook.py"
OPENCODE_INSTALLER = ROOT / "install_opencode_plugin.py"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def install_unified(args) -> None:
    """Install unified hook with automatic source detection."""
    dry = ["--dry-run"] if args.dry_run else []

    # Build the unified hook command
    unified_cmd = f"{sys.executable} {UNIFIED_HOOK}"
    if args.handler:
        unified_cmd += f" --handler {args.handler}"

    # Install for Claude (unified hook handles source detection)
    run([
        str(MERGE),
        "--tool", "claude",
        "--path", str(Path("~/.claude/settings.json").expanduser()),
        "--command", f"{unified_cmd} --source claude",
    ] + dry)

    # Install for Gemini
    run([
        str(MERGE),
        "--tool", "gemini",
        "--path", str(Path("~/.gemini/settings.json").expanduser()),
        "--command", f"{unified_cmd} --source gemini",
    ] + dry)

    # Install for Cursor
    run([
        str(MERGE),
        "--tool", "cursor",
        "--path", str(Path("~/.cursor/hooks.json").expanduser()),
        "--command", f"{unified_cmd} --source cursor",
    ] + dry)

    # Install OpenCode advanced plugin (has its own source detection)
    run([
        str(OPENCODE_INSTALLER),
        "--name", args.name,
        "--output", str(Path("~/.config/opencode/plugins").expanduser()),
        "--advanced",
    ] + (["--force"] if args.force else []) + dry)


def install_classic(args) -> None:
    """Install classic hooks with tool-specific suffixes."""
    cmd = args.command
    dry = ["--dry-run"] if args.dry_run else []

    run([
        str(MERGE),
        "--tool", "claude",
        "--path", str(Path("~/.claude/settings.json").expanduser()),
        "--command", f"{cmd} --claude",
    ] + dry)

    run([
        str(MERGE),
        "--tool", "gemini",
        "--path", str(Path("~/.gemini/settings.json").expanduser()),
        "--command", f"{cmd} --gemini",
    ] + dry)

    run([
        str(MERGE),
        "--tool", "cursor",
        "--path", str(Path("~/.cursor/hooks.json").expanduser()),
        "--command", f"{cmd} --cursor",
    ] + dry)

    run([
        str(MERGE),
        "--tool", "opencode",
        "--path", str(Path("~/.config/opencode/plugins").expanduser() / f"{args.name}.js"),
    ] + dry)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Install hooks across all AI tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Classic mode (explicit source via suffixes)
  install_all.py --command "/path/to/hook" --name my-hook

  # Unified mode (recommended - automatic source detection)
  install_all.py --unified --handler "/path/to/handler" --name my-hook

  # Unified mode without handler (just normalization and filtering)
  install_all.py --unified --name my-hook
""",
    )
    ap.add_argument("--command", help="Base hook command (classic mode)")
    ap.add_argument("--name", required=True, help="OpenCode plugin filename without extension")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    ap.add_argument(
        "--unified",
        action="store_true",
        help="Use unified hook with automatic source detection (recommended)",
    )
    ap.add_argument(
        "--handler",
        help="Handler script path (unified mode only, receives normalized events)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing OpenCode plugin file",
    )
    args = ap.parse_args()

    if args.unified:
        install_unified(args)
    else:
        if not args.command:
            raise SystemExit("--command is required in classic mode (or use --unified)")
        install_classic(args)


if __name__ == "__main__":
    main()
