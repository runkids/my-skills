---
name: feature-radar-archive
description: |
  Archive a completed, rejected, or covered feature into .feature-radar/archive/ with mandatory
  learning extraction. This is the skill that makes knowledge compound — it doesn't just close
  a feature, it extracts learnings, derives new opportunities, and updates references. Use this
  whenever a feature reaches a terminal state, even if the user just casually mentions finishing something.
  Use when:
  - User says "we just shipped X" or "X is done" or "we finished the auth system"
  - A feature was rejected, deemed not applicable, or already covered by existing work
  - A feature is explicitly deferred with rationale
  - User wants to close out an opportunity from .feature-radar/opportunities/
  Trigger phrases: "archive feature", "mark as done", "this feature is done",
  "close this opportunity", "feature shipped", "reject feature", "we just finished",
  "X is complete", "defer this feature"
---

# Archive Feature

Move a feature to `.feature-radar/archive/` and run the mandatory extraction checklist.

## Deep Read

<HARD-GATE>
Read and follow `reference/DEEP-READ.md` — complete all 6 steps before proceeding.
</HARD-GATE>

## Behavioral Directives

<HARD-GATE>
Read and follow `reference/DIRECTIVES.md`.
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
4. **Checkpoint — Review & Annotate** per `reference/WORKFLOW-PATTERNS.md`

5. **Run extraction checklist**:

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

6. **Remove from opportunities** — if the feature had an `opportunities/` file, delete it
7. **Update base.md** — adjust counts in Tracking Summary

## Archive File Format

Use the format defined in `SPEC.md` § 3.2 (`archive/{nn}-{slug}.md`).

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

## Completion Summary

Follow the template in `reference/DIRECTIVES.md`, with skill name "Archive Complete".
