# Init Command

**Source:** Always `~/.config/skillshare/skills` (use `--source` only if user explicitly requests).

## Flags

**Copy (mutually exclusive):**
- `--copy-from <name|path>` — Import from target/path
- `--no-copy` — Empty source

**Targets (mutually exclusive):**
- `--targets "claude,cursor"` — Specific list
- `--all-targets` — All detected
- `--no-targets` — Skip

**Git (mutually exclusive):**
- `--git` — Init git (recommended)
- `--no-git` — Skip

**Discover (add new agents):**
- `--discover --select "windsurf,kilocode"` — Non-interactive (AI use this)
- `--discover` — Interactive only (NOT for AI)

**Other:**
- `--source <path>` — Custom source (**only if user requests**)
- `--remote <url>` — Set git remote
- `--dry-run` — Preview

## Examples

```bash
skillshare init --no-copy --all-targets --git           # Fresh start
skillshare init --copy-from claude --all-targets --git  # Import from Claude
skillshare init --discover --select "windsurf"          # Add new agents
```
