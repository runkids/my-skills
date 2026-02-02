# Hook Use Cases

Common patterns for AI coding agent hooks across Claude Code, Cursor, OpenCode, and Gemini CLI.

## Table of Contents

- [Safety & Security](#safety--security)
- [Auto-formatting & Linting](#auto-formatting--linting)
- [Testing](#testing)
- [Notifications](#notifications)
- [Logging & Audit](#logging--audit)
- [Context Injection](#context-injection)
- [CI/CD Integration](#cicd-integration)

---

## Safety & Security

Block dangerous operations before they execute.

### Block Dangerous Commands

**When**: PreToolUse / beforeShellExecution / tool.execute.before / BeforeTool

```bash
#!/bin/bash
# block-dangerous.sh - Block rm -rf, force push, etc.

read -r INPUT
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .command // ""')

if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/|git\s+push.*--force|DROP\s+TABLE'; then
  echo '{"continue":false,"decision":"deny","reason":"Blocked: dangerous command"}'
  exit 0
fi

echo '{"continue":true,"decision":"allow"}'
```

**Config (Claude)**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "/path/to/block-dangerous.sh"}]
    }]
  }
}
```

### Block Sensitive Files

**When**: PreToolUse (Write/Edit/Read tools)

```bash
#!/bin/bash
# block-sensitive.sh - Prevent reading/writing .env, credentials

read -r INPUT
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

if echo "$FILE" | grep -qE '\.(env|pem|key)$|credentials|secrets'; then
  echo '{"continue":false,"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Blocked: sensitive file"}}'
  exit 0
fi

echo '{"continue":true}'
```

**Config (Claude)**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit|Read",
      "hooks": [{"type": "command", "command": "/path/to/block-sensitive.sh"}]
    }]
  }
}
```

---

## Auto-formatting & Linting

Run formatters after AI edits files.

### Run Formatter on Save

**When**: PostToolUse (Write/Edit) / afterFileEdit / tool.execute.after

```bash
#!/bin/bash
# auto-format.sh - Format files after AI edits

read -r INPUT
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .file_path // ""')

case "$FILE" in
  *.py) python -m black "$FILE" 2>&1 ;;
  *.js|*.ts|*.jsx|*.tsx) npx prettier --write "$FILE" 2>&1 ;;
  *.go) gofmt -w "$FILE" 2>&1 ;;
esac

echo '{"continue":true}'
```

**Config (Claude)**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{"type": "command", "command": "/path/to/auto-format.sh"}]
    }]
  }
}
```

### Run Linter

**When**: PostToolUse / afterFileEdit

```bash
#!/bin/bash
# lint-check.sh - Run linter and report issues

read -r INPUT

cd "$(echo "$INPUT" | jq -r '.cwd // "."')"

RESULT=$(npm run lint 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "{\"continue\":true,\"systemMessage\":\"Lint errors:\\n$RESULT\"}"
else
  echo '{"continue":true}'
fi
```

---

## Testing

Run tests after code changes.

### Auto-run Tests

**When**: PostToolUse / afterFileEdit / tool.execute.after

```bash
#!/bin/bash
# auto-test.sh - Run tests after file changes

read -r INPUT
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .file_path // ""')

# Only run tests for source files
if [[ "$FILE" =~ \.(py|js|ts|go)$ ]]; then
  case "$FILE" in
    *.py) RESULT=$(python -m pytest -q 2>&1) ;;
    *.js|*.ts) RESULT=$(npm test 2>&1) ;;
    *.go) RESULT=$(go test ./... 2>&1) ;;
  esac

  echo "{\"continue\":true,\"systemMessage\":\"Test results:\\n$RESULT\"}"
else
  echo '{"continue":true}'
fi
```

### Type Check (TypeScript/Python)

```bash
#!/bin/bash
# type-check.sh

read -r INPUT
cd "$(echo "$INPUT" | jq -r '.cwd // "."')"

RESULT=$(npx tsc --noEmit 2>&1 || python -m mypy . 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "{\"continue\":true,\"systemMessage\":\"Type errors:\\n$RESULT\"}"
else
  echo '{"continue":true}'
fi
```

---

## Notifications

Alert when tasks complete.

### macOS Desktop Notification

**When**: Stop / stop / event (session end)

```bash
#!/bin/bash
# notify-done.sh - macOS notification

osascript -e 'display notification "Task completed" with title "AI Agent" sound name "Glass"'
echo '{"continue":true}'
```

**Config (Cursor)**:
```json
{
  "version": 1,
  "hooks": {
    "stop": [{"command": "/path/to/notify-done.sh"}]
  }
}
```

### Slack Notification

```bash
#!/bin/bash
# slack-notify.sh

WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

read -r INPUT
TOOL=$(echo "$INPUT" | jq -r '.tool_name // "task"')

curl -s -X POST "$WEBHOOK_URL" \
  -H 'Content-type: application/json' \
  -d "{\"text\":\"AI agent completed: $TOOL\"}" > /dev/null

echo '{"continue":true}'
```

### Discord Notification

```bash
#!/bin/bash
# discord-notify.sh

WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/WEBHOOK"

read -r INPUT
TOOL=$(echo "$INPUT" | jq -r '.tool_name // "task"')

curl -s -X POST "$WEBHOOK_URL" \
  -H 'Content-type: application/json' \
  -d "{\"content\":\"AI agent completed: $TOOL\"}" > /dev/null

echo '{"continue":true}'
```

---

## Logging & Audit

Track AI agent activity.

### Log All Tool Calls

**When**: PreToolUse + PostToolUse / tool.execute.before + after

```bash
#!/bin/bash
# log-tool.sh

LOG_FILE="$HOME/.ai-agent-logs/$(date +%Y-%m-%d).log"
mkdir -p "$(dirname "$LOG_FILE")"

read -r INPUT
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
TOOL=$(echo "$INPUT" | jq -r '.tool_name // .tool // "unknown"')
ARGS=$(echo "$INPUT" | jq -c '.tool_input // .args // {}')

echo "[$TIMESTAMP] $TOOL: $ARGS" >> "$LOG_FILE"
echo '{"continue":true}'
```

### Compliance Audit Trail

```bash
#!/bin/bash
# audit.sh - Structured audit log

AUDIT_FILE="$HOME/.ai-audit/audit.jsonl"
mkdir -p "$(dirname "$AUDIT_FILE")"

read -r INPUT

ENTRY=$(jq -n \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg user "$USER" \
  --arg cwd "$PWD" \
  --argjson input "$INPUT" \
  '{timestamp: $ts, user: $user, cwd: $cwd, event: $input}')

echo "$ENTRY" >> "$AUDIT_FILE"
echo '{"continue":true}'
```

---

## Context Injection

Add context before operations.

### Session Start Context (Gemini)

**When**: SessionStart - fires at startup, resume, clear

```bash
#!/bin/bash
# session-context.sh - Inject project context at session start
# stdout MUST be valid JSON only, use stderr for debug

PROJECT_DIR="${GEMINI_PROJECT_DIR:-$PWD}"
cd "$PROJECT_DIR" 2>/dev/null

GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "N/A")
NODE_VER=$(node --version 2>/dev/null || echo "N/A")

CONTEXT="Branch: $GIT_BRANCH | Node: $NODE_VER"

# Escape for JSON
ESCAPED=$(echo "$CONTEXT" | jq -Rs .)
echo "{\"systemMessage\":$ESCAPED}"
```

**Config (Gemini)**:
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "name": "session-context",
        "type": "command",
        "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/session-context.sh",
        "timeout": 3000
      }]
    }]
  }
}
```

### Add Git Status to Prompts

**When**: UserPromptSubmit / chat.message / BeforeTool / BeforeAgent

```bash
#!/bin/bash
# add-git-context.sh

read -r INPUT

GIT_STATUS=$(git status --short 2>/dev/null)
GIT_BRANCH=$(git branch --show-current 2>/dev/null)

if [ -n "$GIT_STATUS" ]; then
  CONTEXT="Current branch: $GIT_BRANCH\nModified files:\n$GIT_STATUS"
  echo "{\"continue\":true,\"systemMessage\":\"$CONTEXT\"}"
else
  echo '{"continue":true}'
fi
```

### Add Project Context

```bash
#!/bin/bash
# project-context.sh - Add project info to context

read -r INPUT

# Read project description if exists
if [ -f "README.md" ]; then
  SUMMARY=$(head -50 README.md)
  echo "{\"continue\":true,\"systemMessage\":\"Project context:\\n$SUMMARY\"}"
else
  echo '{"continue":true}'
fi
```

---

## CI/CD Integration

Trigger CI/CD workflows.

### Trigger GitHub Actions

**When**: Stop / tool.execute.after (for specific tools)

```bash
#!/bin/bash
# trigger-ci.sh

REPO="owner/repo"
WORKFLOW="test.yml"
TOKEN="${GITHUB_TOKEN}"

curl -s -X POST \
  "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"ref":"main"}' > /dev/null

echo '{"continue":true}'
```

### Auto-commit Changes

**When**: Stop (be careful with this)

```bash
#!/bin/bash
# auto-commit.sh - Commit AI changes

read -r INPUT

cd "$(echo "$INPUT" | jq -r '.cwd // "."')"

if git diff --quiet; then
  echo '{"continue":true}'
  exit 0
fi

git add -A
git commit -m "AI agent: auto-commit changes"

echo '{"continue":true,"systemMessage":"Changes committed"}'
```

---

## Gemini-Specific Patterns

Patterns using Gemini CLI's extended hooks (11 events).

### Mock Model Response (BeforeModel)

**When**: BeforeModel - useful for testing without API calls

```bash
#!/bin/bash
# mock-model.sh

read -r INPUT

if [ -n "$GEMINI_MOCK_MODE" ]; then
  echo '{"decision":"mock","mock_response":{"text":"[MOCKED] Test response"}}'
else
  echo '{"decision":"allow"}'
fi
```

### Redact Sensitive Output (AfterModel)

**When**: AfterModel - filter sensitive info from model responses

```bash
#!/bin/bash
# redact-secrets.sh

read -r INPUT
RESPONSE=$(echo "$INPUT" | jq -r '.model_response.text // ""')

# Redact API keys, tokens
REDACTED=$(echo "$RESPONSE" | sed -E 's/[A-Za-z0-9]{32,}/[REDACTED]/g')

if [ "$RESPONSE" != "$REDACTED" ]; then
  echo "{\"redacted_response\":{\"text\":\"$REDACTED\"}}"
else
  echo '{"decision":"allow"}'
fi
```

### Session Cleanup (SessionEnd)

**When**: SessionEnd - cleanup resources, save state

```bash
#!/bin/bash
# session-cleanup.sh

LOG_DIR="$HOME/.gemini/logs"
mkdir -p "$LOG_DIR"
echo "Session ended: $(date)" >> "$LOG_DIR/sessions.log"

# Cleanup temp files
rm -rf /tmp/gemini-session-* 2>/dev/null

echo '{}'
```

---

## Cross-Tool Implementation

### OpenCode Plugin Example

```js
// ~/.config/opencode/plugins/auto-format.js
// Note: Uses spawn for safe subprocess execution

const { spawn } = require("child_process");
const path = require("path");

function runCommand(cmd, args) {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { stdio: "ignore" });
    proc.on("close", resolve);
    proc.on("error", resolve);
  });
}

module.exports = async function AutoFormatPlugin(pluginInput) {
  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "write" && input.tool !== "edit") return;

      const filePath = output?.args?.file_path;
      if (!filePath) return;

      const ext = path.extname(filePath);
      try {
        switch (ext) {
          case ".py":
            await runCommand("python", ["-m", "black", filePath]);
            break;
          case ".js":
          case ".ts":
            await runCommand("npx", ["prettier", "--write", filePath]);
            break;
        }
      } catch (e) {
        // Silent fail - don't block
      }
    },
  };
};
```

### Multi-Tool Script

```bash
#!/bin/bash
# universal-hook.sh - Detect source and adapt behavior

read -r INPUT

# Detect which tool called us
if echo "$INPUT" | jq -e '.hookSpecificOutput' > /dev/null 2>&1; then
  SOURCE="claude"
elif echo "$INPUT" | jq -e '.version' > /dev/null 2>&1; then
  SOURCE="cursor"
else
  SOURCE="gemini"
fi

# Extract command regardless of format
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .command // .args.command // ""')

# Common logic
if echo "$COMMAND" | grep -q 'rm -rf'; then
  case "$SOURCE" in
    claude)
      echo '{"continue":false,"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Blocked"}}'
      ;;
    cursor)
      echo '{"continue":false,"permission":"deny","user_message":"Blocked"}'
      ;;
    gemini)
      echo '{"decision":"deny","reason":"Blocked"}'
      ;;
  esac
  exit 0
fi

echo '{"continue":true,"decision":"allow"}'
```
