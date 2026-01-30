# Tool Reference

Complete reference for all supported tools: config paths, events, payloads, templates.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Claude Code](#claude-code)
- [Gemini CLI](#gemini-cli)
- [Cursor](#cursor)
- [OpenCode](#opencode)
- [CLI Wrapper](#cli-wrapper)
- [Field Mapping](#field-mapping)

---

## Quick Reference

| Tool | Config | Pre-event | Post-event | Nesting |
|------|--------|-----------|------------|---------|
| Claude | `~/.claude/settings.json` | PreToolUse | PostToolUse | nested |
| Gemini | `~/.gemini/settings.json` | BeforeTool | AfterTool | nested |
| Cursor | `~/.cursor/hooks.json` | beforeShellExecution | afterFileEdit | flat |
| OpenCode | `~/.config/opencode/plugins/*.js` | tool.execute.before | tool.execute.after | plugin |

---

## Claude Code

### Events

| Event | Matcher | Description |
|-------|---------|-------------|
| PreToolUse | ✓ | Before tool execution |
| PostToolUse | ✓ | After tool execution |
| UserPromptSubmit | ✗ | Before prompt sent |
| PermissionRequest | ✓ | Permission dialog |
| Stop | ✗ | Agent completes |
| SessionStart | ✗ | Session begins |
| SessionEnd | ✗ | Session ends |

Matcher patterns: `"Bash"` (exact), `"Write|Edit"` (OR), `"*"` (all)

### Config Template

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "<hook>"}]}
    ]
  }
}
```

### PreToolUse I/O

**Input:**
```json
{"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": "/project", "session_id": "..."}
```

**Allow:**
```json
{"hookSpecificOutput": {"permissionDecision": "allow"}}
```

**Deny:**
```json
{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "Blocked"}, "continue": false}
```

**Modify:**
```json
{"hookSpecificOutput": {"permissionDecision": "allow", "modifiedToolInput": {"command": "ls -la"}}}
```

### PostToolUse I/O

**Input:**
```json
{"tool_name": "Write", "tool_input": {...}, "tool_output": {...}, "cwd": "/project"}
```

**Output:**
```json
{"continue": true, "systemMessage": "File formatted successfully"}
```

---

## Gemini CLI

### Config Locations (Priority)

1. Project: `.gemini/settings.json`
2. User: `~/.gemini/settings.json`
3. System: `/etc/gemini-cli/settings.json`

### Events

| Event | Matcher | Description | Influence |
|-------|---------|-------------|-----------|
| SessionStart | ✗ | Session begins (startup/resume/clear) | Inject context |
| SessionEnd | ✗ | Session ends (exit/clear) | Advisory |
| BeforeAgent | ✗ | After user prompt, before planning | Block turn / context |
| AfterAgent | ✗ | Agent loop ends | Retry / halt |
| BeforeModel | ✗ | Before LLM request | Block / mock |
| AfterModel | ✗ | After LLM response | Filter / redact |
| BeforeToolSelection | ✗ | Before tool selection | Filter tools |
| BeforeTool | ✓ | Before tool execution | Validate / block |
| AfterTool | ✓ | After tool execution | Process / hide |
| PreCompress | ✗ | Before context compression | Advisory |
| Notification | ✗ | System notification | Advisory |

Matcher: regex for tool events (`BeforeTool`, `AfterTool`), exact string for lifecycle.

### Config Template

```json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "write_file|replace",
        "hooks": [
          {
            "name": "security-check",
            "type": "command",
            "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/security.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

### Hook Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | ✓ | Execution engine (only `"command"`) |
| `command` | ✓ | Shell command to execute |
| `name` | ✗ | Friendly identifier for logs/CLI |
| `timeout` | ✗ | Timeout in ms (default: 60000) |
| `description` | ✗ | Brief explanation |

### Environment Variables

```bash
GEMINI_PROJECT_DIR   # Project root absolute path
GEMINI_SESSION_ID    # Current session unique ID
GEMINI_CWD           # Current working directory
CLAUDE_PROJECT_DIR   # Compatibility alias
```

### Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | Preferred for all logic (including deny) |
| 2 | System block | Critical abort |
| Other | Warning | Non-fatal, continues with original params |

**Golden Rule**: stdout must be valid JSON. Use stderr for debug.

### BeforeTool I/O

**Input:**
```json
{
  "hook_name": "BeforeTool",
  "tool_name": "run_shell_command",
  "tool_input": {"command": "ls"},
  "session_id": "..."
}
```

**Allow:**
```json
{"decision": "allow"}
```

**Allow + Context:**
```json
{"decision": "allow", "systemMessage": "Extra context"}
```

**Deny:**
```json
{"decision": "deny", "reason": "Blocked", "systemMessage": "..."}
```

### SessionStart I/O

**Input:**
```json
{"hook_name": "SessionStart", "session_id": "...", "trigger": "startup"}
```

**Output:**
```json
{"systemMessage": "Context injected at session start"}
```

### Managing Hooks (CLI)

```bash
/hooks panel           # View all hooks
/hooks enable-all      # Enable all
/hooks disable-all     # Disable all
/hooks enable <name>   # Enable specific hook
/hooks disable <name>  # Disable specific hook
```

---

## Cursor

### Events

| Event | Description |
|-------|-------------|
| beforeShellExecution | Before shell command |
| afterFileEdit | After file modified |
| stop | Task completes |

### Config Template

```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [{"command": "<hook>"}]
  }
}
```

### beforeShellExecution I/O

**Input:**
```json
{"command": "ls", "cwd": "/project"}
```

**Allow:**
```json
{"continue": true, "permission": "allow"}
```

**Deny:**
```json
{"continue": false, "permission": "deny", "agent_message": "Blocked"}
```

---

## OpenCode

**Critical**: Plugin must export a **function**, not an object.

### Plugin Locations

- Project: `.opencode/plugins/`
- Global: `~/.config/opencode/plugins/`
- npm: Add to `opencode.json` `plugin` array

### Events

| Event | Description |
|-------|-------------|
| tool.execute.before | Before tool execution |
| tool.execute.after | After tool execution |
| command.executed | After command runs |
| file.edited | File was edited |
| file.watcher.updated | File watcher triggered |
| session.created | Session started |
| session.idle | Session became idle |
| session.compacted | Context compressed |
| permission.ask | Permission requested |
| chat.message | Chat message sent |
| event | All events (passive) |

### Context Object

```js
export const MyPlugin = async ({ project, client, $, directory, worktree }) => {
  // project: current project info
  // client: OpenCode SDK client
  // $: Bun shell API (for running commands)
  // directory: working directory
  // worktree: git worktree path
  return { /* hooks */ };
};
```

### Plugin Template

```js
export const MyPlugin = async ({ directory, $ }) => {
  return {
    "tool.execute.before": async (input, output) => {
      // input.tool, input.sessionID, input.callID
      // output.args (mutable)
      if (input.tool === "read" && output.args.filePath?.includes(".env")) {
        throw new Error("Blocked: .env files");  // throw to block
      }
    },

    "tool.execute.after": async (input, output) => {
      // output.title, output.output, output.metadata
      console.log(`Completed: ${input.tool}`);
    },

    "event": async ({ event }) => {
      if (event.type === "session.idle") {
        await $`osascript -e 'display notification "Done!"'`;
      }
    },
  };
};
```

### All Available Hooks

```js
{
  "tool.execute.before": async (input, output) => {},
  "tool.execute.after": async (input, output) => {},
  "command.execute.before": async (input, output) => {},
  "chat.message": async (input, output) => {},
  "chat.params": async (input, output) => {},
  "chat.headers": async (input, output) => {},  // add custom headers
  "permission.ask": async (input, output) => {},
  "event": async ({ event }) => {},
  "config": async (config) => {},  // modify config
}
```

---

## CLI Wrapper

For tools **without** hooks API (gh, aws, kubectl, docker).

### Flow

```
User → ~/.local/bin/gh (wrapper) → Pre-hook → /usr/bin/gh → Post-hook → Exit
```

### Install

```bash
scripts/install_cli_wrapper.py --cli gh --hook "/path/to/hook"
```

### Pre-hook I/O

**Input:**
```json
{"cli": "gh", "args": ["pr", "create"], "cwd": "/project", "phase": "pre"}
```

**Allow:** Exit 0 or `{"decision": "allow"}`

**Deny:**
```json
{"decision": "deny", "reason": "Blocked"}
```

### Post-hook I/O

**Input:**
```json
{"cli": "gh", "args": ["pr", "create"], "cwd": "/project", "phase": "post", "exit_code": 0}
```

### Templates

| Template | Dependencies | JSON I/O |
|----------|--------------|----------|
| bash | jq | Yes |
| python | None | Yes |
| minimal | None | No (CLI args) |

---

## Field Mapping

### Input Fields

| Field | Claude | Gemini | Cursor | OpenCode |
|-------|--------|--------|--------|----------|
| Tool name | `tool_name` | `tool_name` | - | `input.tool` |
| Command | `tool_input.command` | `tool_input.command` | `command` | `output.args.command` |
| CWD | `cwd` | `$GEMINI_CWD` (env) | `cwd` | `ctx.directory` |
| Session | `session_id` | `session_id` / `$GEMINI_SESSION_ID` | - | `input.sessionID` |
| Project | `cwd` | `$GEMINI_PROJECT_DIR` (env) | - | `ctx.worktree` |

### Output Fields

| Action | Claude | Gemini | Cursor | OpenCode |
|--------|--------|--------|--------|----------|
| Allow | `permissionDecision: "allow"` | `decision: "allow"` | `permission: "allow"` | return |
| Deny | `permissionDecision: "deny"` | `decision: "deny"` | `permission: "deny"` | throw |
| Message | `systemMessage` | `systemMessage` | `agent_message` | console.log |

---

## External Docs

- Claude: https://docs.anthropic.com/en/docs/claude-code/hooks
- Gemini: https://geminicli.com/docs/hooks/
- Cursor: https://docs.cursor.com/agent/hooks
