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

Read `.feature-radar/base.md` for project context and existing references. If it doesn't exist, run the `feature-radar` skill first to bootstrap.

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
4. **Assess impact** — does this observation imply:
   - A new opportunity or feature idea? → mention it, suggest creating `opportunities/{nn}-{slug}.md`
   - A way to enhance existing features? → suggest updating relevant opportunity or `base.md`
   - An ecosystem trend? → suggest updating `specs/ecosystem-trends.md`
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
