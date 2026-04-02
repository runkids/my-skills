---
name: slack
description: Interact with Slack workspaces using browser automation. Use when the user needs to check unread channels, navigate Slack, send messages, extract data, find information, search conversations, or automate any Slack task. Triggers include "check my Slack", "what channels have unreads", "send a message to", "search Slack for", "extract from Slack", "find who said", or any task requiring programmatic Slack interaction.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*)
---

# Slack Automation

Automate Slack workspaces via browser: check unreads, navigate channels, send messages, search conversations, and extract data.

## Quick Start

```bash
# Connect to an existing Slack session (preferred — faster than opening new)
agent-browser connect 9222

# Or open Slack fresh
agent-browser open https://app.slack.com

# Snapshot to discover interactive elements
agent-browser snapshot -i
```

## Core Workflow Pattern

Every Slack interaction follows this loop:

1. **Snapshot** — discover available elements and their refs (`@e1`, `@e2`, etc.)
2. **Act** — click, fill, scroll, or press using the discovered ref
3. **Validate** — re-snapshot or screenshot to confirm the action succeeded
4. **Recover** — if the expected element is missing, see "Error Recovery" below

Refs like `@e14` are session-specific and change between sessions. Never hardcode them — always snapshot first, find the element by its label or role, then use the ref shown.

```bash
# Pattern: snapshot → find ref → act → validate
agent-browser snapshot -i          # 1. discover refs
agent-browser click @eNN           # 2. click the ref you found for your target
agent-browser wait 1000
agent-browser snapshot -i          # 3. validate new state
```

## Key Commands

| Action | Command |
|--------|---------|
| Discover elements | `agent-browser snapshot -i` |
| Structured data | `agent-browser snapshot --json > out.json` |
| Click element | `agent-browser click @eNN` |
| Type into field | `agent-browser fill @eNN "text"` |
| Submit | `agent-browser press Enter` |
| Wait for load | `agent-browser wait --load networkidle` |
| Scroll sidebar | `agent-browser scroll down 300 --selector ".p-sidebar"` |
| Screenshot | `agent-browser screenshot filename.png` |
| Get element text | `agent-browser get text @eNN` |
| Check errors | `agent-browser errors` |

## Best Practices

- **Always snapshot before acting** — refs change every session, so discover them fresh.
- **Re-snapshot after navigation** — clicking a tab or channel loads new elements with new refs.
- **Pace rapid interactions** — add `agent-browser wait 500` between quick actions to let the UI settle.
- **Use JSON snapshots for extraction** — `snapshot --json` gives machine-readable output for parsing channels, messages, and metadata.
- **Capture evidence** — screenshot after key actions to document findings.

## Error Recovery

When an expected element is not found in the snapshot:

1. **Screenshot** to see the actual page state: `agent-browser screenshot debug.png`
2. **Scroll** — the element may be off-screen: `agent-browser scroll down 300 --selector ".p-sidebar"`
3. **Wait and re-snapshot** — the page may still be loading: `agent-browser wait --load networkidle && agent-browser snapshot -i`
4. **Check URL** — verify you are in the right section: `agent-browser get url`
5. **Check errors** — look for page-level issues: `agent-browser errors`

## Detailed Task Examples

See [references/slack-tasks.md](references/slack-tasks.md) for step-by-step walkthroughs of common tasks including checking unreads, navigating channels, searching messages, extracting data, and monitoring activity.

See [templates/slack-report-template.md](templates/slack-report-template.md) for a structured report template to document Slack analysis findings.
