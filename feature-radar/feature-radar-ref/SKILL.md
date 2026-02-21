---
name: feature-radar-ref
description: |
  Record external observations, creative inspiration, ecosystem trends, and research findings
  into the feature-radar knowledge base (.feature-radar/references/).
  Use when:
  - You found an interesting approach, technique, or design in another project
  - An ecosystem trend is emerging (new tools, standards, community patterns)
  - A related project shipped a notable feature or solved a problem creatively
  - A user comparison or question reveals a gap or opportunity
  - You discovered research, articles, or talks with relevant insights
  Trigger phrases: "add reference", "log observation", "track this project",
  "ecosystem observation", "interesting approach", "save inspiration"
---

# Add Reference

Record external observations into `.feature-radar/references/`.

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

1. **Identify the source** — ask the user what they observed:
   - Interesting project, technique, or creative approach?
   - Ecosystem trend or emerging pattern?
   - Notable feature or solution from a related project?
   - User comparison, feedback, or question?
   - Research, article, or talk with relevant insights?
2. **Gather context** — URL, date, key details. If the user provides a GitHub URL, fetch the issue/PR for full context.
3. **Classify** — determine the right file:
   - Existing reference file → append a new entry
   - New topic → create `.feature-radar/references/{topic}.md`
4. **Assess impact**:

<HARD-GATE>
Before writing to references/, assess impact by answering ALL of these:
- New opportunity or feature idea? → state yes/no, suggest file if yes
- Way to enhance existing features? → state yes/no, suggest update if yes
- Ecosystem trend? → state yes/no, suggest specs/ecosystem-trends.md update if yes
</HARD-GATE>
5. **Checkpoint** — State what was written and the impact assessment results. Ask: "I've updated `references/{topic}.md`. Does this look correct, or should I adjust anything?" Wait for user confirmation before proceeding.
6. **Update base.md** — increment the references count in Tracking Summary

## File Format

```markdown
# {Topic}

> {One-line summary of what this reference tracks}

## {Date} — {Entry Title}

**Source**: {URL}

{What happened and why it matters to us}

**Implications**:
- {What this means for our project}
```

## Naming Convention

Name by the subject being tracked, not the event:

- Good: `vercel-skills-ecosystem.md`, `agent-path-conventions.md`, `cli-ux-patterns.md`
- Bad: `2026-02-18-update.md`, `interesting-finding.md`

## Guidelines

- Always cite source URLs and dates for traceability.
- Append new entries chronologically to existing files — don't create a new file per observation.
- Be objective. Record what happened, then assess implications separately.
- If the observation reveals an unmet need or innovation opportunity, proactively suggest creating an opportunity.
- Look for creative inspiration, not just feature gaps — how others solve problems can spark new ideas.

## Example Output

```
→ Appended to references/cli-ux-patterns.md
→ Suggested: new opportunity "interactive config wizard"
→ Updated base.md: references 3 → 3 (appended, not new file)
```

## Completion Summary

When all steps are done, present:

```
── Feature Radar: Ref Complete ──

Files created:  + {path} (new)
Files updated:  ~ {path} (what changed)
Counts: archive {n}, opportunities {n}, specs {n}, references {n}
Next suggested action: {recommendation}
```

Do not end with "this should work" or "try this". End with the summary above.
