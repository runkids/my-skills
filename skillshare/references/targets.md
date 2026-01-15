# Target Management

## target

Manages sync targets.

```bash
skillshare target list                        # List all targets
skillshare target claude                      # Show target info
skillshare target add myapp ~/.myapp/skills   # Add custom target
skillshare target remove myapp                # Remove target
```

## Sync Modes

```bash
skillshare target claude --mode merge         # Individual skill symlinks (default)
skillshare target claude --mode symlink       # Entire directory symlinked
```

**Mode comparison:**

| Mode | Behavior | Local Skills |
|------|----------|--------------|
| `merge` | Creates individual symlinks for each skill | Preserved |
| `symlink` | Entire target directory is a symlink | Not possible |

## Safe Target Removal

```bash
skillshare target remove <name>     # Safe: only removes link
# NOT: rm -rf ~/.target/skills      # Dangerous: may delete source
```
