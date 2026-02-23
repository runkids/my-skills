# my-skills

My personal AI agent skills — managed and synced with [**skillshare**](https://github.com/runkids/skillshare).

## Install

### [skillshare](https://github.com/runkids/skillshare)

One source of truth. Sync everywhere with one command.

```bash
# Install skillshare
curl -fsSL https://raw.githubusercontent.com/runkids/skillshare/main/install.sh | sh

# Install all skills from this repo
skillshare install runkids/my-skills
skillshare sync

# Or pick a specific skill
skillshare install runkids/my-skills -s vue-best-practices
skillshare sync
```

## How It Works

### Folder Organization

Skills are organized into category folders for easy browsing. On `skillshare sync`, nested paths **auto-flatten** into each target — no manual mapping needed.

```text
~/.config/skillshare/skills/
├── frontend/
│   ├── frontend-design/
│   ├── ui-skills/
│   ├── react/
│   │   ├── react-best-practices/
│   │   └── react-doctor/
│   └── vue/
│       ├── vue-best-practices/
│       ├── vue-debug-guides/
│       └── ...
├── devops/
│   └── docker-expert/
├── web-dev/
│   ├── accessibility/
│   ├── core-web-vitals/
│   ├── performance/
│   └── ...
└── utils/
    ├── ascii-box-check/
    ├── remotion/
    └── skill-creator/

         ↓ skillshare sync

├→ Claude Code   (~/.claude/skills/)
├→ Cursor        (~/.cursor/skills/)
├→ Codex         (~/.codex/skills/)
├→ OpenCode      (~/.config/opencode/skills/)
└→ 45+ more targets...
```

### .skillignore

Like `.gitignore`, but for skills. Exclude folders from sync without removing them from the repo.

```text
# .skillignore
skillshare       # meta tools — not a skill
feature-radar    # WIP, not ready to share
```

### Sync Modes

skillshare supports per-target sync modes:

| Mode | Behavior |
| ------ | ---------- |
| **symlink** | Link to source (default on macOS/Linux) |
| **copy** | Real files in target |
| **merge** | Preserve target's local skills, add shared ones |

### Security Audit

Every `skillshare install` runs a built-in audit to scan for prompt injection, data exfiltration, and credential theft.

```bash
# Manual audit anytime
skillshare audit
```

## Why skillshare?

> One source of truth for AI CLI skills. Sync everywhere with one command.

- **49+ AI tools** — Claude Code, Cursor, Codex, Copilot, Gemini, and more
- **Single binary** — written in Go, no runtime dependencies
- **Cross-machine sync** — Git-native `push` / `pull`
- **Privacy-first** — no telemetry, no central registry
- **Web dashboard** — `skillshare ui` for visual management

Learn more: [github.com/runkids/skillshare](https://github.com/runkids/skillshare)

## License

MIT
