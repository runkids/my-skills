# Init Command

Initializes skillshare configuration.

## Copy Source Flags (mutually exclusive)

| Flag | Description |
|------|-------------|
| `--copy-from <name\|path>` | Copy skills from target name or directory path |
| `--no-copy` | Start with empty source |

## Target Flags (mutually exclusive)

| Flag | Description |
|------|-------------|
| `--targets <list>` | Comma-separated targets: `"claude,cursor,codex"` |
| `--all-targets` | Add all detected CLI targets |
| `--no-targets` | Skip target setup |

## Git Flags (mutually exclusive)

| Flag | Description |
|------|-------------|
| `--git` | Initialize git in source (recommended) |
| `--no-git` | Skip git initialization |

## Other Flags

| Flag | Description |
|------|-------------|
| `--source <path>` | Custom source directory |
| `--remote <url>` | Set git remote (implies `--git`) |
| `--dry-run` | Preview without making changes |

## Examples

```bash
# Fresh start with all targets and git
skillshare init --no-copy --all-targets --git

# Copy from Claude, specific targets
skillshare init --copy-from claude --targets "claude,cursor" --git

# Minimal setup
skillshare init --no-copy --no-targets --no-git

# Custom source with remote
skillshare init --source ~/my-skills --remote git@github.com:user/skills.git
```
