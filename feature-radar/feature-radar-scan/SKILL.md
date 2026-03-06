---
name: feature-radar-scan
description: |
  Discover new feature opportunities from creative brainstorming, user feedback, ecosystem
  trends, and cross-project research. Writes results to .feature-radar/opportunities/.
  MUST use this skill when the user wants to GENERATE new ideas — not evaluate existing ones.
  Trigger on any request to brainstorm, explore, discover, or find new feature ideas, even
  casual ones like "I wonder what else we could do" or "give me ideas".
  Use when the user:
  - Asks "what else could we build?", "give me feature ideas", "what are we missing?"
  - Wants to brainstorm, explore new directions, or refresh the opportunity backlog
  - Says "scan ecosystem", "scan opportunities", "find new features"
  - Asks to review GitHub issues, community feedback, or adjacent tools for inspiration
  - Mentions "explore", "discover", or "new directions" in a feature context
  Do NOT use for evaluating/prioritizing existing features — that's feature-radar's job.
---

# Scan Opportunities

Discover new feature opportunities and add them to `.feature-radar/opportunities/`.

## Deep Read

<HARD-GATE>
Read and follow `../feature-radar/references/DEEP-READ.md` — complete all 6 steps before proceeding.
</HARD-GATE>

## Behavioral Directives

<HARD-GATE>
Read and follow `../feature-radar/references/DIRECTIVES.md`.

Additional directive for this skill:
- **Filter aggressively** — Do NOT create opportunity files for weak signals. If you can't cite concrete demand evidence, skip it.
</HARD-GATE>

## Workflow

1. **Identify sources** — where to look for ideas:
   - **User signals**: issues, discussions, forum posts, support requests
   - **Creative exploration**: "what if we..." brainstorming, combining existing features in new ways
   - **Ecosystem evolution**: adjacent tools, emerging standards, new capabilities in dependencies
   - **Technical possibilities**: new APIs, libraries, or techniques that enable things previously impossible
   - **Cross-project research**: interesting approaches from related projects (from base.md Inspiration Sources)
   - **Community conversations**: Reddit, HN, Discord, blog posts
2. **Scan and collect** — for each source, look for:
   - Unmet user needs and recurring pain points
   - Feature ideas with demand signals (upvotes, comments, multiple independent asks)
   - Creative approaches that could enhance existing functionality
   - Technical breakthroughs that unlock new possibilities
   - Patterns emerging across multiple tools
3. **Deduplicate** — check against existing `opportunities/` and `archive/` files
4. **Cross-reference codebase** — for each candidate, search the project to check:
   - Already partially implemented? → mark as "Partially Done"
   - Does existing architecture support this? → note in "Design Notes"
   - Related TODOs or FIXMEs in the code? → cite them
5. **Evaluate each candidate**:

<HARD-GATE>
Before creating any opportunity file, evaluate the candidate against ALL 6 criteria.
Each criterion must be explicitly addressed — do not skip any.
</HARD-GATE>

| Criterion | Question |
|-----------|----------|
| **Real user demand** | Are users actually asking for this, or does it solve a latent need? |
| **Value uplift** | Does this meaningfully improve the user experience or unlock new possibilities? |
| **Innovation potential** | Does this introduce a creative breakthrough or unique approach? |
| **Effort / impact ratio** | Is the cost justified by the benefit? |
| **Architectural fit** | Does it align with our core philosophy? |
| **Ecosystem timing** | Is the ecosystem ready? |

6. **Create opportunity files** — for each viable candidate, write `.feature-radar/opportunities/{nn}-{slug}.md`
7. **Checkpoint — Review & Annotate** per `../feature-radar/references/WORKFLOW-PATTERNS.md`

Present scan results using this format:

```
Scan complete: {n} new opportunities
| # | Opportunity | Demand Signal | Impact | Effort | Source |
|---|------------|---------------|--------|--------|--------|
| {nn} | {title} | {evidence} | H/M/L | H/M/L | {where found} |
```

8. **Update base.md** — increment opportunities count, update Value & Innovation Landscape if needed

## Opportunity File Format

Use the format defined in `SPEC.md` § 3.3 (`opportunities/{nn}-{slug}.md`).

## Guidelines

- Don't create opportunities for every idea you find. Filter aggressively — weak signal wastes attention.
- 1 issue with no comments = weak signal. Multiple independent asks = strong signal.
- Creative ideas without existing demand can still be valid — evaluate innovation potential separately.
- Write an honest "Our Position" — it's OK to say "we don't want this" or "not yet."
- Number sequentially from the highest existing number in `opportunities/` and `archive/`.
- If scanning reveals problems others have that we've already solved, add to `references/` instead.

## Example Output

```
→ Created opportunities/07-streaming-output.md (Impact: High, Effort: Medium)
→ Skipped: "hook system" already exists as opportunities/03-hook-system.md
→ Updated base.md: opportunities 6 → 7
```

## Completion Summary

Follow the template in `../feature-radar/references/DIRECTIVES.md`, with skill name "Scan Complete".
