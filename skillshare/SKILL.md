---
name: skillshare
description: Manage and sync skills across AI CLI tools
---

# Skillshare CLI

Use skillshare to manage skills shared across multiple AI CLI tools.

## Commands

### Check Status
```bash
skillshare status
```
Shows source directory, skill count, and sync state for all targets.

### Sync Skills
```bash
skillshare sync           # Sync all targets
skillshare sync --dry-run # Preview changes
```
Pushes skills from source to all configured targets.

### Pull Local Skills
```bash
skillshare pull claude    # Pull from specific target
skillshare pull --all     # Pull from all targets
```
Copies skills created in target directories back to source.

### View Differences
```bash
skillshare diff           # All targets
skillshare diff claude    # Specific target
```

### Manage Targets
```bash
skillshare target list              # List all targets
skillshare target add myapp ~/path  # Add custom target
skillshare target remove myapp      # Remove target
```

### Backup & Restore
```bash
skillshare backup --list    # List backups
skillshare backup --cleanup # Clean old backups
skillshare restore claude   # Restore from backup
```

## Typical Workflow

1. Create/edit skills in any target directory (e.g., ~/.claude/skills/)
2. Run `skillshare pull` to bring changes to source
3. Run `skillshare sync` to distribute to all targets
4. Commit changes: `cd ~/.config/skillshare/skills && git add . && git commit`

## Tips

- Source directory: ~/.config/skillshare/skills
- Config file: ~/.config/skillshare/config.yaml
- Use `skillshare doctor` to diagnose issues
