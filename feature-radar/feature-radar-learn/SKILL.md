---
name: feature-radar:learn
description: |
  Extract reusable patterns, architectural decisions, and pitfalls from completed work
  into the feature-radar knowledge base (.feature-radar/specs/).
  Use when:
  - You just shipped a feature and want to capture what you learned
  - You discovered a reusable pattern worth documenting
  - You made an architectural decision that future work should know about
  - You hit a pitfall others should avoid
  Trigger phrases: "extract learnings", "capture what we learned", "document this pattern",
  "save this decision", "what did we learn"
---

# Extract Learnings

Capture reusable knowledge from completed work into `.feature-radar/specs/`.

## Prerequisites

Read `.feature-radar/base.md` for project context. If it doesn't exist, run the `feature-radar` skill first to bootstrap.

## Workflow

1. **Identify the source** — ask the user what was just completed (feature, bug fix, refactor, investigation)
2. **Analyze the work** — review recent commits, changed files, and implementation decisions
3. **Extract knowledge** — identify what's reusable:
   - **Patterns**: recurring solutions worth replicating (e.g., "three-tier config merge")
   - **Decisions**: architectural choices with rationale (e.g., "YAML over JSON because...")
   - **Pitfalls**: mistakes or dead ends others should avoid
   - **Techniques**: implementation approaches that worked well
4. **Write to specs** — create or append to `.feature-radar/specs/{topic}.md`
5. **Update base.md** — increment the specs count in Tracking Summary

## File Format

```markdown
# {Topic}

## Context
{What was being built or solved}

## Pattern / Decision / Pitfall
{The reusable knowledge}

## Why It Matters
{When future work would benefit from this}
```

## Guidelines

- One topic per file. If the learning spans multiple topics, create multiple files.
- Name files by the pattern, not by the feature that produced it.
  - Good: `yaml-config-merge.md`, `symlink-vs-copy-tradeoffs.md`
  - Bad: `audit-feature-learnings.md`, `v2-refactor-notes.md`
- Append to existing files when the new learning extends a known topic.
- Keep it concise — future readers need the insight, not the full story.
