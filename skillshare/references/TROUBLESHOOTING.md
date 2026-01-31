# Skillshare Troubleshooting

Common issues, solutions, and tips for AI assistants.

## Common Issues

| Problem | Diagnosis | Solution |
|---------|-----------|----------|
| "config not found" | Config missing | Run `skillshare init` |
| Target shows differences | Files out of sync | Run `skillshare sync` |
| Lost source files | Deleted via symlink | `cd ~/.config/skillshare/skills && git checkout -- <skill>/` |
| Target has local skills | Need to preserve | Ensure `merge` mode, then `skillshare collect` before sync |
| Skill not appearing | Not synced yet | Run `skillshare sync` after install |
| Can't find installed skills | Wrong directory | Check `skillshare status` for source path |
| "permission denied" | Symlink issues | Check file ownership and permissions |
| Git remote not set | Push fails | Run `git remote add origin <url>` in source |

## Recovery Workflow

When something goes wrong:

```bash
skillshare doctor          # 1. Diagnose issues
skillshare backup          # 2. Create safety backup
skillshare sync --dry-run  # 3. Preview fix
skillshare sync            # 4. Apply fix
```

## Git Recovery

If source files were accidentally deleted:

```bash
cd ~/.config/skillshare/skills
git status                     # See what's missing
git checkout -- <skill-name>/  # Restore specific skill
git checkout -- .              # Restore all deleted files
```

If you need to restore from backup:

```bash
skillshare backup --list               # List available backups
skillshare restore claude --from <timestamp>
```

## Tips for AI Assistants

### Symlink Behavior

Understanding symlinks is critical:

1. **merge mode** (default): Each skill in target is a symlink to source
   - Editing `~/.claude/skills/my-skill/SKILL.md` edits the source
   - Changes are immediate and affect all targets
   - Safe: `skillshare uninstall my-skill`
   - **DANGEROUS**: `rm -rf ~/.claude/skills/my-skill` - deletes source!

2. **symlink mode**: Entire target directory is a symlink
   - `~/.claude/skills` → `~/.config/skillshare/skills`
   - All targets are identical
   - No local skills possible

### When to Use --dry-run

Always use `--dry-run` in these situations:

- User is cautious or new to skillshare
- Before `sync` on first use
- Before `collect --all` to see what will be imported
- Before `install` from unknown sources
- Before `restore` to preview what will change
- Before `target remove` to understand impact

### Safe vs Dangerous Operations

**Safe operations:**
```bash
skillshare target remove <name>     # Removes symlinks, keeps source
skillshare uninstall <name>         # Removes skill properly
skillshare sync                     # Creates/updates symlinks
```

**NEVER do this:**
```bash
rm -rf ~/.claude/skills/my-skill    # Deletes source via symlink!
rm -rf ~/.claude/skills             # May delete entire source!
```

### Creating New Skills

Guide users to create skills in source:

1. Create directory: `~/.config/skillshare/skills/<skill-name>/`
2. Create `SKILL.md` with required frontmatter:
   ```yaml
   ---
   name: skill-name
   description: What this skill does
   ---
   ```
3. Run `skillshare sync` to distribute

### Git Workflow Reminders

After any skill changes, remind user to push:

```bash
skillshare push                    # Simple: commit + push
skillshare push -m "Add new skill" # With custom message
```

### Handling Init Prompts

AI cannot respond to CLI prompts. When user asks to initialize:

1. Ask clarifying questions in chat
2. Build the command with appropriate flags
3. Run non-interactively

Example conversation:
- AI: "Do you have existing skills to copy from Claude or another tool?"
- User: "Yes, from Claude"
- AI: "Which CLI tools should I set up as targets?"
- User: "Claude and Cursor"
- AI: "Should I initialize git for version control?"
- User: "Yes"
- AI runs: `skillshare init --copy-from claude --targets "claude,cursor" --git`

### Debugging Sync Issues

If sync seems stuck or wrong:

```bash
skillshare status        # Check current state
skillshare diff          # See actual differences
ls -la ~/.claude/skills  # Check symlink targets
```

Look for:
- Broken symlinks (pointing to non-existent files)
- Regular files instead of symlinks
- Wrong symlink targets
