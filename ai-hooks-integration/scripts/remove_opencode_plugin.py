#!/usr/bin/env python3
"""Remove an OpenCode plugin file by path.

Usage:
  remove_opencode_plugin.py --path ~/.config/opencode/plugins/<name>.js
"""

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = ap.parse_args()

    path = Path(args.path).expanduser()
    if not path.exists():
        print(f"[skip] file not found: {path}")
        return
    if args.dry_run:
        print(f"[dry-run] remove {path}")
        return
    path.unlink()
    print(f"[removed] {path}")


if __name__ == "__main__":
    main()
