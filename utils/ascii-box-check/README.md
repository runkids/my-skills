# ascii-box-check

Verify and fix ASCII box-drawing diagram alignment in markdown files.

## Install

### Option 1: skillshare

Install with [skillshare](https://github.com/runkids/skillshare) to sync this skill across all your AI CLI tools:

```bash
# Install skillshare (if you haven't already)
curl -fsSL https://raw.githubusercontent.com/runkids/skillshare/main/skills/skillshare/scripts/run.sh | sh -s -- init

# Install this skill
skillshare install runkids/my-skills -s ascii-box-check
skillshare sync
```

### Option 2: Skills CLI

Install with [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add runkids/my-skills -s ascii-box-check
```

## Problem

ASCII box diagrams look like this:

```
┌─────────────────────────┐
│  Content here           │
│  More content           │
└─────────────────────────┘
```

Every line must have the **same display width**. Off-by-one spacing errors are invisible to the eye but break rendering in some terminals and editors.

## Scripts

### `scripts/check.py`

Scan markdown files for misaligned boxes:

```bash
python3 scripts/check.py website/docs
```

Output when issues found:

```
Found 2 misaligned lines:

  docs/commands/audit.md:46  expected=63 actual=62
    │  path: /Users/alice/.config/skillshare/skills              │

  docs/commands/audit.md:65  expected=40 actual=39
    │  Warning:  2 (1 high, 1 medium)     │
```

Exit code `0` = all aligned, `1` = issues found.

### `scripts/pad_line.py`

Generate a correctly padded box line:

```bash
python3 scripts/pad_line.py 67 "│  your content here"
# │  your content here                                              │
#   (display width: 67)
```

Arguments:
1. `width` — target display width (must match the ┌...┐ line)
2. `content` — everything before the trailing padding (e.g. `│  text`)

## Why Display Width Matters

| Expression | Result | What it measures |
|-----------|--------|-----------------|
| `len('│')` | 1 | Python code points |
| `'│'.encode('utf-8')` | 3 bytes | UTF-8 byte length |
| `east_asian_width('│')` | `N` (narrow) | Terminal display columns = **1** |
| `east_asian_width('中')` | `W` (wide) | Terminal display columns = **2** |

The scripts use `unicodedata.east_asian_width()` to correctly compute how many terminal columns each character occupies.
