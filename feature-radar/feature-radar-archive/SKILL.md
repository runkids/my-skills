---
name: feature-radar:archive
description: |
  Archive a completed, rejected, or covered feature into the feature-radar tracking system
  (.feature-radar/archive/) with mandatory learning extraction.
  Use when:
  - A feature just shipped and needs to be recorded
  - A feature was rejected or deemed not applicable
  - An existing capability already covers a requested feature
  - A feature is explicitly deferred with rationale
  Trigger phrases: "archive feature", "mark as done", "this feature is done",
  "close this opportunity", "feature shipped", "reject feature"
---

# Archive Feature

Move a feature to `.feature-radar/archive/` and run the mandatory extraction checklist.

## Prerequisites

<HARD-GATE>
Before starting, verify and complete ALL:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. Read `.feature-radar/base.md`
3. From base.md, identify: **Project Language**, **Key Feature Areas**, **Inspiration Sources**
4. Use this context in ALL subsequent decisions
</HARD-GATE>

## Workflow

1. **Identify the feature** — ask the user which feature to archive. Check `opportunities/` for an existing file to move.
2. **Determine status**:
   - **Done** — fully implemented and working
   - **Covered** — existing functionality handles the use case
   - **Rejected** — decided against implementing
   - **N/A** — not applicable to our architecture
   - **Deferred** — valuable but postponed with rationale
3. **Create archive file** — write `.feature-radar/archive/{nn}-{slug}.md`
4. **Run extraction checklist**:

### Extraction Checklist

<HARD-GATE>
Complete ALL 5 checks below. For each check, you MUST explicitly state the finding.
Do NOT proceed to step 5 until every check has a written response.

□ archive/{nn}-{slug}.md created with correct status
□ Extract learnings      → specs/{topic}.md
□ Derive new opportunities → opportunities/{nn}-{slug}.md
□ Update references       → references/{topic}.md
□ Update ecosystem trends → specs/ecosystem-trends.md

Acceptable responses per check:
- "No learnings to extract" — acceptable, but must be stated
- "New opportunity identified: {description}" — create the file
- "No reference updates needed" — acceptable, but must be stated
</HARD-GATE>

5. **Remove from opportunities** — if the feature had an `opportunities/` file, delete it
6. **Update base.md** — adjust counts in Tracking Summary

## Archive File Format

```markdown
# {N}. {Feature Name}

**Status**: {Done | Covered | Rejected | N/A | Deferred}
**Ref**: {upstream issue/PR links, if any}
**Implemented**: {code paths / commits, if Done}

## Description
{What the feature does and why it was requested}

## Implementation Notes
{Key decisions, trade-offs, and anything future maintainers should know}
```

## Guidelines

- The extraction checklist is NOT optional. Every archive action must go through all 5 checks.
- If the feature was in `opportunities/`, use the same number. If it's new, use the next available number.
- "Deferred" is not a trash bin — include a clear rationale and conditions for re-evaluation.

## Example Output

```
→ Moved opportunities/04-config-merge.md → archive/04-config-merge.md (Done)
→ Learnings: specs/yaml-config-merge.md (new)
→ New opportunity: opportunities/09-config-validation.md
→ References: no updates | Ecosystem: no changes
→ Updated base.md: archive 3→4, specs 2→3
```
