# Install, Update & Uninstall

## install

```bash
# GitHub
skillshare install owner/repo                    # Browse repo for skills
skillshare install owner/repo/path/to/skill      # Direct path
skillshare install git@github.com:user/repo.git  # SSH

# Local
skillshare install ~/Downloads/my-skill

# Team repo (tracked for updates)
skillshare install github.com/team/skills --track
```

| Flag | Description |
|------|-------------|
| `--name <n>` | Custom name |
| `--force, -f` | Overwrite existing |
| `--update, -u` | Update if exists |
| `--track, -t` | Track for `update` |
| `--dry-run, -n` | Preview |

**Tracked repos:** Prefix `_`, nested `__` (e.g., `_team__frontend__ui`).

After install: `skillshare sync`

## update

```bash
skillshare update my-skill       # From stored source
skillshare update _team-repo     # Git pull tracked repo
skillshare update --all          # All tracked repos
skillshare update _repo --force  # Discard local changes
```

After update: `skillshare sync`

## uninstall

```bash
skillshare uninstall my-skill          # With confirmation
skillshare uninstall my-skill --force  # Skip confirmation
```

After uninstall: `skillshare sync`

## new

Create a new skill template.

```bash
skillshare new <name>           # Create SKILL.md template
skillshare new <name> --dry-run # Preview
```

After create: Edit SKILL.md → `skillshare sync`
