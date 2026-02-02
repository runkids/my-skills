---
name: skillshare
version: 0.8.1
description: Syncs skills across AI CLI tools from a single source of truth. Use when asked to "sync skills", "collect skills", "pull from remote", "show status", "list skills", "install skill", "initialize skillshare", "search skills", or manage skill targets.
argument-hint: "[command] [target] [--dry-run]"
---

# Skillshare CLI

```
Source: ~/.config/skillshare/skills  ← Single source of truth
         ↓ sync (symlinks)
Targets: ~/.claude/skills, ~/.cursor/skills, ...
```

## Quick Start

```bash
skillshare status              # Check state
skillshare sync --dry-run      # Preview
skillshare sync                # Execute
```

## Commands

| Task | Command |
|------|---------|
| **Status** | `status`, `diff`, `list --verbose`, `doctor` |
| **Sync** | `sync`, `sync --dry-run` |
| **Create** | `new <name>` → `sync` |
| **Search** | `search <query>`, `search --list`, `search --json` |
| **Install** | `install <source>` → `sync` |
| **Team repo** | `install <url> --track` → `sync` |
| **Collect** | `collect <target>` → `sync` |
| **Update** | `update <name>`, `update --all` → `sync` |
| **Remove** | `uninstall <name>` → `sync` |
| **Git sync** | `push -m "msg"`, `pull` |
| **Targets** | `target add <n> <p>`, `target remove <n>`, `target <n> --mode merge\|symlink` |
| **Upgrade** | `upgrade`, `upgrade --cli`, `upgrade --skill` |

## Init (Non-Interactive)

**AI must use flags** — cannot respond to CLI prompts.

```bash
# Step 1: Check existing skills
ls ~/.claude/skills ~/.cursor/skills 2>/dev/null | head -10

# Step 2: Run based on findings
skillshare init --copy-from claude --all-targets --git  # If skills exist
skillshare init --no-copy --all-targets --git           # Fresh start

# Step 3: Verify
skillshare status
```

**Add new agents later:**
```bash
skillshare init --discover --select "windsurf,kilocode"
```

See [init.md](references/init.md) for all flags.

## Safety

**NEVER** `rm -rf` symlinked skills — deletes source. Use `skillshare uninstall`.

## References

| Topic | File |
|-------|------|
| Init flags | [init.md](references/init.md) |
| Sync/pull/push | [sync.md](references/sync.md) |
| Install/update | [install.md](references/install.md) |
| Status/diff/list | [status.md](references/status.md) |
| Target management | [targets.md](references/targets.md) |
| Backup/restore | [backup.md](references/backup.md) |
| Troubleshooting | [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) |
