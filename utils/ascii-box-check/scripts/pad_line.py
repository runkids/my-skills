#!/usr/bin/env python3
"""Generate a correctly padded ASCII box line.

Usage:
  python3 pad_line.py <width> <content>

Example:
  python3 pad_line.py 67 "│  your content here"
  # Output: │  your content here                                            │
"""
import sys, unicodedata


def dw(s):
    """Display width: CJK = 2 columns, everything else = 1."""
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 pad_line.py <width> <content>")
        print('Example: python3 pad_line.py 67 "│  hello world"')
        sys.exit(1)

    width = int(sys.argv[1])
    content = sys.argv[2]
    pad = width - dw(content) - 1  # -1 for closing │

    if pad < 0:
        print(f"Error: content width ({dw(content)+1}) exceeds box width ({width})", file=sys.stderr)
        sys.exit(1)

    result = content + " " * pad + "│"
    print(result)
    print(f"  (display width: {dw(result)})")
