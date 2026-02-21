---
name: feature-radar-learn
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
5. **Checkpoint** — State what was written and ask: "I've written to `specs/{topic}.md` ({classification type}). Does this look correct, or should I adjust anything?" Wait for user confirmation before proceeding.
6. **Update base.md** — increment the specs count in Tracking Summary

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

## Completion Summary

When all steps are done, present:

```
── Feature Radar: Learn Complete ──

Files created:  + {path} (new)
Files updated:  ~ {path} (what changed)
Counts: archive {n}, opportunities {n}, specs {n}, references {n}
Next suggested action: {recommendation}
```

Do not end with "this should work" or "try this". End with the summary above.
