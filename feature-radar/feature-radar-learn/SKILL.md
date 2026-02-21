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

<HARD-GATE>
Before starting, verify and complete ALL:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. Read `.feature-radar/base.md`
3. From base.md, identify: **Project Language**, **Key Feature Areas**, **Inspiration Sources**
4. Use this context in ALL subsequent decisions
</HARD-GATE>

## Workflow

1. **Identify the source** — ask the user what was just completed (feature, bug fix, refactor, investigation)
2. **Analyze the work** — review recent commits, changed files, and implementation decisions
3. **Extract knowledge** — identify what's reusable:
   - **Patterns**: recurring solutions worth replicating (e.g., "three-tier config merge")
   - **Decisions**: architectural choices with rationale (e.g., "YAML over JSON because...")
   - **Pitfalls**: mistakes or dead ends others should avoid
   - **Techniques**: implementation approaches that worked well
<HARD-GATE>
Before writing to specs/, classify each piece of knowledge into exactly one category:
- **Pattern**: recurring solution worth replicating
- **Decision**: architectural choice with rationale
- **Pitfall**: mistake or dead end to avoid
- **Technique**: implementation approach that worked well

State the classification explicitly in your output.
</HARD-GATE>

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

## Example Output

```
→ Created specs/symlink-vs-copy-tradeoffs.md (Decision)
→ Updated base.md: specs 2 → 3
```
