---
name: ascii-box-check
description: >-
  Verify and fix ASCII box-drawing diagram alignment in markdown files.
  Use when editing or creating box diagrams (┌─┐│└─┘), checking docs
  for misaligned boxes, or after bulk-editing documentation with diagrams.
allowed-tools: "Bash(python3:*)"
metadata:
  author: runkids
  version: 1.0.0
---

# ASCII Box Alignment Check

Verify that all lines within an ASCII box-drawing diagram have consistent display width.

## When to Use

Use this skill when:
- Editing or creating ASCII box-drawing diagrams in markdown
- Reviewing documentation PRs that contain box diagrams
- After bulk edits to files with box art (e.g. updating counts, adding rows)

Do NOT use for:
- Non-box ASCII art (trees, tables, plain indented text)

## Core Rule

**Every line in a box (┌ top, │ body, └ bottom) must have the same display width.**

Display width ≠ byte count ≠ `len()`. Box-drawing chars (┌─┐│└┘┤├┬┴┼) are 1 column each (same as ASCII). CJK characters are 2 columns.

## Scripts

### Verify alignment

Scan all `.md` files under a directory for misaligned boxes:

```bash
python3 scripts/check.py <directory>
```

- Exit code 0 = all aligned
- Exit code 1 = misaligned lines found (prints file:line, expected vs actual width)

The script path is relative to this skill directory. Use the full path when invoking:

```bash
python3 .claude/skills/ascii-box-check/scripts/check.py website/docs
```

### Generate a padded line

Produce a correctly padded │ line for a given box width:

```bash
python3 scripts/pad_line.py <width> "<content>"
```

Example:

```bash
python3 .claude/skills/ascii-box-check/scripts/pad_line.py 67 "│  your content here"
# Output: │  your content here                                            │
#   (display width: 67)
```

## Fixing Misalignment

1. **Identify the reference width** — the ┌───...───┐ top border defines the box width
2. **Adjust padding** — use `pad_line.py` to generate correct │ lines
3. **Re-run verification** — always run `check.py` after fixing to confirm

## Common Pitfalls

| Pitfall | Why it happens |
|---------|---------------|
| Off-by-one padding | Manually adding/removing spaces without counting |
| `len()` vs display width | `len('│')` = 3 bytes in UTF-8, but display width = 1 |
| CJK text in boxes | Each CJK char is 2 columns wide |
| Editing without column ruler | Edit tool doesn't show column positions |

## Key Principle

**Never eyeball alignment** — always run the verification script. The human eye cannot reliably distinguish N spaces from N±1 spaces in a monospace font.
