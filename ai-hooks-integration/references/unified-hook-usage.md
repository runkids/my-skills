# Unified Hook Usage Guide

The unified hook system solves cross-tool interference issues when multiple AI tools share configuration files.

## Quick Start

```bash
# Install unified hooks across all tools
scripts/install_all.py --unified --handler "/path/to/handler.py" --name my-hook

# Preview changes without writing
scripts/install_all.py --unified --handler "/path/to/handler.py" --name my-hook --dry-run
```

## Problem Background

Cursor and OpenCode read `~/.claude/settings.json`, which triggers Claude's hooks even when running inside these other tools. This causes:

1. **Source misidentification**: Events report `source=claude` when actually from Cursor/OpenCode
2. **Noise events**: Cursor reading `.claude/` directory generates unwanted events
3. **Duplicate events**: OpenCode triggers both Claude hook AND its own plugin

## How It Works

The unified hook (`scripts/runtime/unified_hook.py`) sits between the tool and your handler:

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────┐
│  Tool   │ --> │ unified_hook │ --> │   Handler    │ --> │ Output  │
│(Claude) │     │  (detect,    │     │ (your logic) │     │  JSON   │
└─────────┘     │  filter,     │     └──────────────┘     └─────────┘
                │  normalize)  │
                └──────────────┘
```

### 1. Source Detection

Walks the process tree (up to 8 levels) looking for tool signatures:

```python
TOOL_SIGNATURES = {
    "cursor": ["cursor", "/cursor/"],
    "opencode": ["opencode", "/opencode/"],
    "gemini": ["gemini", "/gemini/"],
    "windsurf": ["windsurf", "/windsurf/"],
    "zed": ["/zed/", "zed.app"],
}
```

The detected source **overrides** the claimed `--source` parameter.

### 2. Event Filtering

Drops noise events before they reach your handler:

| Source | Condition | Action | Reason |
|--------|-----------|--------|--------|
| `opencode` | Any | Drop | Handled by dedicated plugin |
| `cursor` | cwd contains `.claude` | Drop | Config reading noise |
| `cursor` | command contains `.claude` | Drop | Config reading noise |

### 3. Event Normalization

Converts tool-specific payloads to a canonical format:

```json
{
  "event_type": "PreToolUse",
  "source": "cursor",           // Detected, not claimed
  "session_id": "abc123",
  "cwd": "/path/to/project",
  "tool_name": "Bash",
  "tool_input": {"command": "npm test"},
  "timestamp": "2025-01-15T10:30:00Z",
  "raw_payload": { ... }        // Original for debugging
}
```

## Command Line Options

```
unified_hook.py [options]

Options:
  --source {claude,gemini,cursor,opencode}
                      Claimed source (may be overridden by detection)
  --event-type TYPE   Event type for normalization (default: PreToolUse)
  --handler PATH      Python script to process normalized events
  --no-detect         Disable automatic source detection
  --no-filter         Disable event filtering
  --normalize-only    Output normalized event without running handler

Environment:
  HOOK_DEBUG=1        Enable debug logging to stderr
  HOOK_LOG_FILE       Log to file instead of stderr
```

## Writing a Handler

Your handler receives normalized events on stdin and outputs response JSON:

```python
#!/usr/bin/env python3
import json
import sys

def main():
    event = json.load(sys.stdin)

    # Your logic here
    tool = event["tool_name"]
    source = event["source"]
    command = event.get("tool_input", {}).get("command", "")

    # Example: Block rm -rf from any source
    if "rm -rf" in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked"
            },
            "continue": False
        }))
        return

    # Allow by default
    print(json.dumps({
        "hookSpecificOutput": {"permissionDecision": "allow"},
        "continue": True
    }))

if __name__ == "__main__":
    main()
```

## OpenCode Plugin

OpenCode uses a dedicated plugin (not the unified hook) because:

1. It doesn't use JSON stdin/stdout like other tools
2. It needs persistent WebSocket connections for efficiency
3. It can detect when running inside other AI tools

Install with `--advanced` for full features:

```bash
scripts/install_opencode_plugin.py --name my-hook \
  --output ~/.config/opencode/plugins --advanced
```

Features of advanced plugin:
- WebSocket + HTTP fallback
- Session ID from cwd hash
- Idle timeout detection (SessionEnd after 5 min)
- Other AI tool detection (avoids duplicates)

## Debug Mode

Enable debug logging to see what's happening:

```bash
# Log to stderr
HOOK_DEBUG=1 echo '{"tool_name":"Bash"}' | python unified_hook.py

# Log to file
HOOK_DEBUG=1 HOOK_LOG_FILE=/tmp/hook.log python unified_hook.py
```

Example debug output:
```
[unified_hook] Received payload: {"tool_name":"Bash",...
[unified_hook] Source override: claude -> cursor
[unified_hook] Effective source: cursor
[unified_hook] Event dropped: Cursor reading .claude directory
```

## Testing

Test source detection:
```bash
python scripts/runtime/detect_source.py
```

Test event normalization:
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
  python scripts/runtime/unified_hook.py --normalize-only
```

Test with a handler:
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
  python scripts/runtime/unified_hook.py --handler /path/to/handler.py
```

## Canonical Event Schema

See `references/schemas/canonical-event.schema.json` for the full JSON Schema.

See `references/contracts/canonical-event-contract.yaml` for field mappings from each tool.
