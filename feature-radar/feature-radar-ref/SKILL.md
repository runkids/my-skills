---
name: feature-radar-ref
description: |
  Record external observations, creative inspiration, ecosystem trends, and research findings
  into .feature-radar/references/. This is the skill for capturing anything interesting from
  outside your project — other tools, articles, competitor approaches, community discussions.
  Use this whenever the user mentions seeing something cool elsewhere or wants to bookmark
  an external insight for future reference.
  Use when:
  - User says "I saw this cool thing in Stripe's API" or "check out how X handles this"
  - An ecosystem trend is emerging (new tools, standards, community patterns)
  - A related project shipped a notable feature worth noting
  - User shares a URL, article, talk, or research finding with relevant insights
  - A user comparison or question reveals a gap or opportunity
  Trigger phrases: "add reference", "log observation", "track this project",
  "ecosystem observation", "interesting approach", "save inspiration"
---

# Add Reference

Record external observations into `.feature-radar/references/`.

## Deep Read

<HARD-GATE>
Read and follow `reference/DEEP-READ.md` — complete all 6 steps before proceeding.
</HARD-GATE>

## Behavioral Directives

<HARD-GATE>
Read and follow `reference/DIRECTIVES.md`.
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

Use the format defined in `SPEC.md` § 3.5 (`references/{topic}.md`).

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

Follow the template in `reference/DIRECTIVES.md`, with skill name "Ref Complete".
