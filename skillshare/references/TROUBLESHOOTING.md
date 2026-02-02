# Troubleshooting

## Quick Fixes

| Problem | Solution |
|---------|----------|
| "config not found" | `skillshare init` |
| Target shows differences | `skillshare sync` |
| Lost source files | `cd ~/.config/skillshare/skills && git checkout -- .` |
| Skill not appearing | `skillshare sync` after install |
| Git push fails | `git remote add origin <url>` in source |

## Recovery

```bash
skillshare doctor          # Diagnose
skillshare backup          # Safety backup
skillshare sync --dry-run  # Preview
skillshare sync            # Fix
```

## Git Recovery

```bash
cd ~/.config/skillshare/skills
git checkout -- <skill>/   # Restore specific
git checkout -- .          # Restore all
```

## AI Assistant Notes

### Symlink Safety

- **merge mode** (default): Per-skill symlinks. Edit anywhere = edit source.
- **symlink mode**: Entire directory symlinked.

**Safe:** `skillshare uninstall`, `target remove`

**DANGEROUS:** `rm -rf` on symlinked skills deletes source!

### When to Use --dry-run

- First-time users
- Before `sync`, `collect --all`, `restore`
- Before `install` from unknown sources

### Init (Non-Interactive)

AI cannot respond to CLI prompts. Always use flags:

```bash
skillshare init --copy-from claude --all-targets --git
```

### Debug Sync

```bash
skillshare status
skillshare diff
ls -la ~/.claude/skills  # Check symlinks
```
