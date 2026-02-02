#!/usr/bin/env python3
"""Remove hook entries from Claude/Gemini/Cursor JSON configs.

Usage:
  remove_hooks.py --tool claude  --path ~/.claude/settings.json --command "<hook-cmd>"
  remove_hooks.py --tool gemini  --path ~/.gemini/settings.json --command "<hook-cmd>"
  remove_hooks.py --tool cursor  --path ~/.cursor/hooks.json     --command "<hook-cmd>"

Behavior:
  - Removes entries whose command contains the provided command string
  - Cleans up empty hook arrays and hooks objects
"""

import argparse
from pathlib import Path

from runtime.tool_config import JSON_TOOLS, get_config, load_json, save_json


def filter_hooks(hooks, nested: bool, command: str):
    """Remove hooks containing the given command string."""
    if not isinstance(hooks, list):
        return []
    kept = []
    for h in hooks:
        if not isinstance(h, dict):
            kept.append(h)
            continue
        if nested:
            inner = h.get("hooks", []) if isinstance(h, dict) else []
            new_inner = []
            for ih in inner:
                cmd = ih.get("command", "") if isinstance(ih, dict) else ""
                if command not in cmd:
                    new_inner.append(ih)
            if new_inner:
                h = dict(h)
                h["hooks"] = new_inner
                kept.append(h)
        else:
            cmd = h.get("command", "") if isinstance(h, dict) else ""
            if command not in cmd:
                kept.append(h)
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", choices=JSON_TOOLS, required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = ap.parse_args()

    path = Path(args.path).expanduser()
    data = load_json(path)

    hooks = data.get("hooks", {})
    cfg = get_config(args.tool)
    key = cfg["hook_key"]
    nested = cfg.get("nested", False)

    if key in hooks:
        hooks[key] = filter_hooks(hooks[key], nested, args.command)
        if not hooks[key]:
            hooks.pop(key, None)

    if isinstance(hooks, dict) and not hooks:
        data.pop("hooks", None)

    save_json(path, data, args.dry_run)


if __name__ == "__main__":
    main()
