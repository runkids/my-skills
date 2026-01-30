#!/usr/bin/env python3
"""Install CLI wrapper for tools without built-in hooks.

Usage:
  # Install wrapper for gh CLI
  install_cli_wrapper.py --cli gh --hook "/path/to/hook"

  # Specify both pre and post hooks
  install_cli_wrapper.py --cli kubectl \\
      --pre-hook "/path/to/pre" \\
      --post-hook "/path/to/post"

  # Use Python template (no jq dependency)
  install_cli_wrapper.py --cli aws --hook "/path/to/hook" --template python

  # Custom output directory
  install_cli_wrapper.py --cli docker --hook "/path/to/hook" --output ~/.local/bin

  # Dry run
  install_cli_wrapper.py --cli gh --hook "/path/to/hook" --dry-run

Notes:
  - Wrapper is installed to ~/.local/bin by default (should be in PATH before /usr/local/bin)
  - Original binary is auto-detected from PATH
  - Use --force to overwrite existing wrapper
  - Hook receives JSON on stdin with: cli, args, cwd, phase (pre/post), exit_code (post only)
"""

import argparse
import os
import sys
from pathlib import Path

# Add runtime module to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime.cli_wrapper import (
    find_original_binary,
    generate_wrapper,
    write_wrapper,
)

DEFAULT_OUTPUT_DIR = Path.home() / ".local" / "bin"


def ensure_path_priority(wrapper_dir: Path) -> None:
    """Print instructions if wrapper directory is not in PATH with priority."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    wrapper_dir_str = str(wrapper_dir.resolve())

    if wrapper_dir_str not in path_dirs:
        print(f"\nWarning: {wrapper_dir} is not in PATH")
        print("Add to your shell profile (~/.bashrc or ~/.zshrc):")
        print(f'  export PATH="{wrapper_dir}:$PATH"')
        return

    # Check priority
    for i, p in enumerate(path_dirs):
        if p == wrapper_dir_str:
            if i > 0:
                print(f"\nNote: {wrapper_dir} is in PATH but not first")
                print("For wrappers to work, it should be before system directories")
            return


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Install CLI wrapper for hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - same hook for pre and post
  install_cli_wrapper.py --cli gh --hook "/path/to/hook"

  # Separate pre and post hooks
  install_cli_wrapper.py --cli kubectl \\
      --pre-hook "/path/to/security-check" \\
      --post-hook "/path/to/audit-log"

  # Python template (cross-platform, no jq)
  install_cli_wrapper.py --cli aws --hook "/path/to/hook" --template python

  # Minimal template (no JSON, args as parameters)
  install_cli_wrapper.py --cli docker --hook "/path/to/hook" --template minimal

Hook Input Format (bash/python templates):
  Pre-hook stdin:  {"cli": "gh", "args": ["pr", "create"], "cwd": "/project", "phase": "pre"}
  Post-hook stdin: {"cli": "gh", "args": ["pr", "create"], "cwd": "/project", "phase": "post", "exit_code": 0}

Hook Output Format (pre-hook only):
  Allow:  {"decision": "allow"}
  Block:  {"decision": "deny", "reason": "Not allowed"}
""",
    )

    ap.add_argument("--cli", required=True, help="CLI name to wrap (e.g., gh, kubectl)")
    ap.add_argument("--hook", help="Hook command for both pre and post")
    ap.add_argument("--pre-hook", help="Pre-execution hook command")
    ap.add_argument("--post-hook", help="Post-execution hook command")
    ap.add_argument("--original", help="Path to original binary (auto-detected if omitted)")
    ap.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for wrapper (default: {DEFAULT_OUTPUT_DIR})",
    )
    ap.add_argument(
        "--template",
        choices=["bash", "python", "minimal"],
        default="bash",
        help="Wrapper template (default: bash, requires jq)",
    )
    ap.add_argument("--timeout", type=int, default=5, help="Hook timeout in seconds")
    ap.add_argument("--force", action="store_true", help="Overwrite existing wrapper")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")

    args = ap.parse_args()

    # Determine hooks
    pre_hook = args.pre_hook or args.hook or ""
    post_hook = args.post_hook or args.hook or ""

    if not pre_hook and not post_hook:
        ap.error("At least one of --hook, --pre-hook, or --post-hook is required")

    # Find original binary
    output_dir = args.output.expanduser()
    original = args.original

    if not original:
        original = find_original_binary(args.cli, exclude_dir=output_dir)
        if not original:
            print(f"Error: Cannot find '{args.cli}' in PATH", file=sys.stderr)
            print("Use --original to specify the path manually", file=sys.stderr)
            sys.exit(1)

    # Verify original exists
    if not Path(original).exists():
        print(f"Error: Original binary not found: {original}", file=sys.stderr)
        sys.exit(1)

    # Generate wrapper
    wrapper_content = generate_wrapper(
        cli_name=args.cli,
        original_path=original,
        pre_hook=pre_hook,
        post_hook=post_hook,
        hook_timeout=args.timeout,
        template=args.template,
    )

    # Write wrapper
    wrapper_path = output_dir / args.cli

    if wrapper_path.exists() and not args.force and not args.dry_run:
        print(f"Error: Wrapper already exists: {wrapper_path}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        sys.exit(1)

    success = write_wrapper(
        output_path=wrapper_path,
        content=wrapper_content,
        force=args.force,
        dry_run=args.dry_run,
    )

    if success:
        if not args.dry_run:
            print(f"Installed: {wrapper_path}")
            print(f"Original:  {original}")
            ensure_path_priority(output_dir)
    else:
        print(f"Error: Failed to write wrapper", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
