# Sync, Collect, Pull & Push Commands

| Type | Command | Direction |
|------|---------|-----------|
| **Local** | `sync` / `collect` | Source ↔ Targets |
| **Remote** | `push` / `pull` | Source ↔ Git Remote |

## sync

```bash
skillshare sync                # Execute
skillshare sync --dry-run      # Preview
skillshare sync --force        # Override conflicts
```

## collect

Import skills from target(s) to source.

```bash
skillshare collect claude      # From specific target
skillshare collect --all       # From all targets
skillshare collect --dry-run   # Preview
```

## pull

Git pull + sync to all targets.

```bash
skillshare pull                # Pull + sync
skillshare pull --dry-run      # Preview
```

## push

Git commit + push source.

```bash
skillshare push                # Default message
skillshare push -m "message"   # Custom message
skillshare push --dry-run      # Preview
```

## Workflows

**Local:** Edit anywhere → `collect` → `sync`

**Cross-machine:** Machine A: `push` → Machine B: `pull`
