---
name: feature-radar:ref
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

## Prerequisites

<HARD-GATE>
Before starting, verify and complete ALL:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. Read `.feature-radar/base.md`
3. From base.md, identify: **Project Language**, **Key Feature Areas**, **Inspiration Sources**
4. Use this context in ALL subsequent decisions
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
5. **Update base.md** — increment the references count in Tracking Summary

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
