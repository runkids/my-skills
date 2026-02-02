# Backup & Restore

```bash
skillshare backup                # All targets
skillshare backup claude         # Specific target
skillshare backup --list         # List backups
skillshare backup --cleanup      # Remove old

skillshare restore claude                            # Latest
skillshare restore claude --from 2026-01-14_21-22   # Specific
```

Backups: `~/.config/skillshare/backups/<timestamp>/`
