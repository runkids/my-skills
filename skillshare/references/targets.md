# Target Management

```bash
skillshare target list                        # List targets
skillshare target claude                      # Show info
skillshare target add myapp ~/.myapp/skills   # Add custom
skillshare target remove myapp                # Safe unlink
```

## Sync Modes

```bash
skillshare target claude --mode merge         # Per-skill symlinks (default)
skillshare target claude --mode symlink       # Entire dir symlinked
```

| Mode | Local Skills | Behavior |
|------|--------------|----------|
| `merge` | Preserved | Individual symlinks |
| `symlink` | Not possible | Single symlink |

**Always use** `target remove` — never `rm -rf` on symlinked targets.
