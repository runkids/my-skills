# Install, Update & Uninstall

## install

Adds a skill from various sources.

```bash
# GitHub shorthand (auto-expands to github.com/...)
skillshare install owner/repo                    # Discovery mode
skillshare install owner/repo/path/to/skill      # Direct path

# Full URLs
skillshare install github.com/user/repo          # Discovery mode
skillshare install github.com/user/repo/skill    # Direct path
skillshare install git@github.com:user/repo.git  # SSH

# Local
skillshare install ~/Downloads/my-skill

# Team repo (preserves .git for updates)
skillshare install github.com/team/skills --track
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--name <name>` | Custom skill name |
| `--force, -f` | Overwrite existing |
| `--update, -u` | Update existing (git pull or reinstall) |
| `--track, -t` | Install as tracked repo (Team Edition) |
| `--dry-run, -n` | Preview without installing |

After install: `skillshare sync`

## update

Updates skills or tracked repos.

```bash
skillshare update my-skill       # Update from stored source
skillshare update _team-repo     # Git pull tracked repo
skillshare update --all          # Update all tracked repos + skills with metadata
skillshare update _repo --force  # Discard local changes and update
```

Safety: Repos with uncommitted changes are blocked by default.
Use `--force` to discard local changes and pull latest.

After update: `skillshare sync`

## uninstall

Removes a skill from source.

```bash
skillshare uninstall my-skill          # With confirmation
skillshare uninstall my-skill --force  # Skip confirmation
skillshare uninstall my-skill --dry-run
```

After uninstall: `skillshare sync`
