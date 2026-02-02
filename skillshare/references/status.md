# Status & Inspection Commands

## status

Shows source location, targets, and sync state.

```bash
skillshare status
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

## search

Search GitHub for skills (repos with SKILL.md).

```bash
skillshare search <query>           # Interactive (select to install)
skillshare search <query> --list    # List only, no install prompt
skillshare search <query> --json    # JSON output for scripting
skillshare search <query> -n 10     # Limit results (default: 20, max: 100)
```

**Requires GitHub auth** (gh CLI or `GITHUB_TOKEN` env var).

## doctor

Checks configuration health and diagnoses issues.

```bash
skillshare doctor
```

## upgrade

Upgrades CLI binary and/or built-in skillshare skill.

```bash
skillshare upgrade              # Both CLI + skill
skillshare upgrade --cli        # CLI only
skillshare upgrade --skill      # Skill only
skillshare upgrade --force      # Skip confirmation
skillshare upgrade --dry-run    # Preview
```

After upgrading skill: `skillshare sync`
