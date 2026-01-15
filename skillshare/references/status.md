# Status & Inspection Commands

## status

Shows source location, targets, and sync state.

```bash
skillshare status
```

**Expected output:**
```
Source: ~/.config/skillshare/skills (4 skills)
Targets:
  claude   ✓ synced   ~/.claude/skills
  codex    ✓ synced   ~/.codex/skills
  cursor   ⚠ 1 diff   ~/.cursor/skills
```

## diff

Shows differences between source and targets.

```bash
skillshare diff                # All targets
skillshare diff claude         # Specific target
```

## list

Lists installed skills.

```bash
skillshare list                # Basic list
skillshare list --verbose      # With source and install info
```

## doctor

Checks configuration health and diagnoses issues.

```bash
skillshare doctor
```
