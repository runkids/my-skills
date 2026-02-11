#!/usr/bin/env python3
"""Scan markdown files for misaligned ASCII box-drawing diagrams."""
import os, sys, unicodedata

BOX_CHARS = set("│└┌├┤┬┴┼─┐┘┏┓┗┛┃┠┨┯┷╋━")


def dw(s):
    """Display width: CJK/Fullwidth = 2 columns, everything else = 1."""
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s
    )


def scan_lines(lines, fpath="<stdin>"):
    """Scan lines for misaligned boxes. Returns list of issues."""
    issues = []
    box, start = [], 0
    in_code_block = False
    for i, line in enumerate(lines, 1):
        s = line.rstrip("\n")
        stripped = s.lstrip()
        # Track code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block and not stripped.startswith("```"):
            # Skip lines outside code blocks that happen to have box chars
            # (box diagrams should be inside ``` blocks or standalone)
            pass
        if stripped.startswith("┌") or stripped.startswith("┏"):
            box, start = [s], i
        elif box:
            box.append(s)
            if stripped.startswith("└") or stripped.startswith("┗"):
                ref = dw(box[0])
                for j, bl in enumerate(box):
                    first = bl.lstrip()[:1]
                    if first and first in BOX_CHARS and dw(bl) != ref:
                        issues.append(
                            (fpath, start + j, ref, dw(bl), bl.rstrip())
                        )
                box = []
    return issues


def scan(target):
    """Scan target (file or directory) for misaligned boxes."""
    if os.path.isfile(target):
        if not target.endswith(".md"):
            print(f"Warning: {target} is not a .md file", file=sys.stderr)
        with open(target) as f:
            return scan_lines(f.readlines(), target)

    issues = []
    for root, _, files in os.walk(target):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                issues.extend(scan_lines(f.readlines(), fpath))
    return issues


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.exists(target):
        print(f"Error: {target} not found", file=sys.stderr)
        sys.exit(2)
    issues = scan(target)
    if issues:
        print(f"Found {len(issues)} misaligned line(s):\n")
        for f, ln, exp, act, txt in issues:
            diff = act - exp
            sign = "+" if diff > 0 else ""
            print(f"  {f}:{ln}  expected={exp} actual={act} ({sign}{diff})")
            print(f"    {txt}\n")
        sys.exit(1)
    else:
        print("All box diagrams aligned.")
