---
name: feature-radar-archive
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

## Deep Read

<HARD-GATE>
Before ANY action, complete ALL steps — do NOT skip or rush:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. **Read base.md thoroughly** — understand Project Context, Feature Inventory, Classification Rules, and current Tracking Summary counts
3. **Scan existing files** — list what's already in archive/, opportunities/, specs/, references/. Read file names and headers to understand current state
4. **Identify context** — extract and state:
   - Project Language & Architecture
   - Key Feature Areas (from Feature Inventory)
   - Inspiration Sources
   - Current counts: {archive: n, opportunities: n, specs: n, references: n}
5. **State your understanding** — in 2-3 sentences, describe what the project does, what's already tracked, and what gaps you see

Proceed to workflow ONLY after completing all 5 steps.
</HARD-GATE>

## Behavioral Directives

<HARD-GATE>
Follow ALL directives throughout this skill's execution:

1. **Read deeply, not superficially** — When reading files, understand the intricacies: relationships between files, naming conventions, architectural patterns. Do NOT skim. If a file references another, follow the reference.
2. **Artifacts over conversation** — Write findings to files, not just chat messages. Every substantive output must persist in `.feature-radar/`.
3. **Do not stop mid-flow** — Complete ALL workflow steps before stopping. If a step yields no results, state "No findings" and continue to the next step.
4. **State what you produced** — After each step, explicitly state: what file was created/updated, what changed, and what's next.
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
4. **Checkpoint — Review & Annotate**

After writing the archive file, tell the user:

"I've written `archive/{nn}-{slug}.md`. Please review it. You can:
1. **Approve as-is** — say 'looks good' or 'continue'
2. **Annotate the file** — add `> NOTE: your correction here` anywhere in the file, then say 'address my notes'
3. **Give verbal feedback** — tell me what to change

I will not proceed until you confirm."

<HARD-GATE>
When the user says "address my notes":
1. Read the file and find ALL lines starting with `> NOTE:`
2. Address each note — modify the surrounding content accordingly
3. Remove the `> NOTE:` lines after addressing them
4. Present a summary of changes made
5. Ask again: "All notes addressed. Anything else to adjust?"

Do NOT proceed to the next step until the user approves.
</HARD-GATE>

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

## Completion Summary

When all steps are done, present:

```
── Feature Radar: Archive Complete ──

Files created:  + {path} (new)
Files updated:  ~ {path} (what changed)
Files removed:  - {path} (why)
Counts: archive {n}, opportunities {n}, specs {n}, references {n}
Next suggested action: {recommendation}
```

Do not end with "this should work" or "try this". End with the summary above.
