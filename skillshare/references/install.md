# Install & Uninstall Commands

## install

Adds a skill from various sources.

```bash
skillshare install github.com/user/repo              # Discovery mode
skillshare install github.com/user/repo/path/skill   # Direct path
skillshare install ~/Downloads/my-skill              # Local path
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--name <name>` | Custom skill name |
| `--force` | Overwrite existing skill |
| `--update` | Update existing (git pull if possible, else reinstall) |

**`--force` vs `--update`:**
- `--update`: Tries `git pull` first (for git repos without subdir), falls back to reinstall
- `--force`: Always delete and reinstall

After install, run `skillshare sync` to distribute to targets.

## uninstall

Removes a skill from source.

```bash
skillshare uninstall my-skill          # With confirmation
skillshare uninstall my-skill --force  # Skip confirmation
```

After uninstall, run `skillshare sync` to update targets.
