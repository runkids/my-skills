---
name: electron
description: "Click UI elements, extract content, navigate menus, fill forms, send messages, and read application state in Electron desktop apps (VS Code, Slack, Discord, Figma, Notion) using agent-browser via Chrome DevTools Protocol. Use when the user needs to click buttons in a desktop app, scrape text from an Electron UI, type into input fields, take screenshots of app windows, switch between app tabs/webviews, or run automated tests against an Electron application. Triggers include 'automate Slack app', 'control VS Code', 'extract data from Discord', 'fill form in Notion', 'screenshot Figma', or any task requiring automation of a native Electron application."
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*)
---

# Electron App Automation

Automate any Electron desktop app using agent-browser. Electron apps are built on Chromium and expose a Chrome DevTools Protocol (CDP) port that agent-browser can connect to, enabling the same snapshot-interact workflow used for web pages.

## Core Workflow

1. **Launch** the Electron app with remote debugging enabled
2. **Connect** agent-browser to the CDP port
3. **Snapshot** to discover interactive elements
4. **Interact** using element refs (click, fill, type)
5. **Re-snapshot** after navigation or state changes

```bash
# Launch an Electron app with remote debugging
open -a "Slack" --args --remote-debugging-port=9222

# Connect agent-browser to the app
agent-browser connect 9222

# Standard workflow from here
agent-browser snapshot -i
agent-browser click @e5
agent-browser screenshot slack-desktop.png
```

## Launching Electron Apps with CDP

Every Electron app supports `--remote-debugging-port` since it is built into Chromium. The pattern is the same across all apps — only the app name/path and port differ.

| Platform | Pattern | Example |
|----------|---------|---------|
| macOS | `open -a "AppName" --args --remote-debugging-port=PORT` | `open -a "Slack" --args --remote-debugging-port=9222` |
| Linux | `app-binary --remote-debugging-port=PORT` | `slack --remote-debugging-port=9222` |
| Windows | `"path\to\app.exe" --remote-debugging-port=PORT` | `"...\slack\slack.exe" --remote-debugging-port=9222` |

**Important:** Quit the app first if already running — the flag must be present at launch time.

See `references/platform-launch-commands.md` for full per-platform examples with common apps.

## Connecting

```bash
# Connect to a specific port
agent-browser connect 9222

# Or use --cdp on each command
agent-browser --cdp 9222 snapshot -i

# Auto-discover a running Chromium-based app
agent-browser --auto-connect snapshot -i
```

After `connect`, all subsequent commands target the connected app without needing `--cdp`.

## Tab and Webview Management

Electron apps often have multiple windows or webviews. Use tab commands to list and switch between them:

```bash
# List all available targets (windows, webviews, etc.)
agent-browser tab
# Example output:
#   0: [page]    Slack - Main Window     https://app.slack.com/
#   1: [webview] Embedded Content        https://example.com/widget

# Switch to a specific tab by index
agent-browser tab 2

# Switch by URL pattern
agent-browser tab --url "*settings*"
```

Electron `<webview>` elements appear as separate targets with `type: "webview"` and can be controlled like regular pages.

## Common Patterns

### Inspect and Navigate an App

```bash
open -a "Slack" --args --remote-debugging-port=9222
sleep 3  # Wait for app to start
agent-browser connect 9222
agent-browser snapshot -i
agent-browser click @e10  # Navigate to a section
agent-browser snapshot -i  # Re-snapshot after navigation
```

### Extract Data from a Desktop App

```bash
agent-browser connect 9222
agent-browser snapshot -i
agent-browser get text @e5
agent-browser snapshot --json > app-state.json
```

### Fill Forms and Send Input

```bash
agent-browser connect 9222
agent-browser snapshot -i
agent-browser fill @e3 "search query"
agent-browser press Enter
agent-browser wait 1000
agent-browser snapshot -i
```

### Take Screenshots

```bash
agent-browser connect 9222
agent-browser screenshot app-state.png
agent-browser screenshot --full full-app.png
agent-browser screenshot --annotate annotated-app.png
```

### Run Multiple Apps Simultaneously

Use named sessions to control multiple Electron apps at the same time:

```bash
agent-browser --session slack connect 9222
agent-browser --session vscode connect 9223
agent-browser --session slack snapshot -i
agent-browser --session vscode snapshot -i
```

## Color Scheme

To preserve dark mode when connecting via CDP:

```bash
agent-browser connect 9222
agent-browser --color-scheme dark snapshot -i
```

Or set globally: `AGENT_BROWSER_COLOR_SCHEME=dark agent-browser connect 9222`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Ensure app was launched with `--remote-debugging-port=NNNN`. Quit and relaunch if it was already running. Check port: `lsof -i :9222` |
| Connect fails after launch | Wait a few seconds (`sleep 3`) — some apps need time to initialize |
| Elements missing in snapshot | App may use multiple webviews. Run `agent-browser tab` to list targets and switch |
| Cannot type in input fields | Use `agent-browser keyboard type "text"` or `agent-browser keyboard inserttext "text"` for custom input components |
