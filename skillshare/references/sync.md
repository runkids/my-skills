# Sync, Pull & Push Commands

## sync

Pushes skills from source to all targets.

```bash
skillshare sync                # Execute sync
skillshare sync --dry-run      # Preview only
```

## pull

Brings skills from target(s) to source.

```bash
skillshare pull claude         # Pull from specific target
skillshare pull --all          # Pull from all targets
skillshare pull --remote       # Pull from git remote + sync all
```

## push

Commits and pushes source to git remote.

```bash
skillshare push                # Default commit message
skillshare push -m "message"   # Custom commit message
skillshare push --dry-run      # Preview only
```

## Workflows

**Local workflow:**
1. Create skill in any target (e.g., `~/.claude/skills/my-skill/`)
2. `skillshare pull claude` - bring to source
3. `skillshare sync` - distribute to all targets

**Cross-machine workflow:**
1. Machine A: `skillshare push` - commit and push to remote
2. Machine B: `skillshare pull --remote` - pull from remote + sync
