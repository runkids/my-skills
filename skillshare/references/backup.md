# Backup & Restore Commands

## backup

Creates backup of target skills.

```bash
skillshare backup                # Backup all targets
skillshare backup claude         # Backup specific target
skillshare backup --list         # List available backups
skillshare backup --cleanup      # Remove old backups
```

Backups stored in: `~/.config/skillshare/backups/<timestamp>/`

## restore

Restores skills from backup.

```bash
skillshare restore claude                               # From latest backup
skillshare restore claude --from 2026-01-14_21-22-18    # From specific backup
```
