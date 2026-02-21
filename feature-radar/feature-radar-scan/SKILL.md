---
name: feature-radar:scan
description: |
  Discover new feature opportunities from multiple sources — creative brainstorming,
  user feedback, ecosystem evolution, technical possibilities, and cross-project research —
  and add them to the feature-radar tracking system (.feature-radar/opportunities/).
  Use when:
  - Brainstorming creative feature ideas or exploring new directions
  - Reviewing user feedback for unmet needs and pain points
  - Exploring adjacent tools and ecosystems for inspiration
  - Identifying technical breakthroughs that enable new possibilities
  - Periodic opportunity refresh to keep the backlog current
  Trigger phrases: "scan opportunities", "find new features", "brainstorm ideas",
  "what could we build", "refresh opportunities", "scan ecosystem", "feature ideas"
---

# Scan Opportunities

Discover new feature opportunities and add them to `.feature-radar/opportunities/`.

## Prerequisites

<HARD-GATE>
Before starting, verify and complete ALL:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. Read `.feature-radar/base.md`
3. From base.md, identify: **Project Language**, **Key Feature Areas**, **Inspiration Sources**
4. Use this context in ALL subsequent decisions
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
7. **Update base.md** — increment opportunities count, update Value & Innovation Landscape if needed

## Opportunity File Format

Use the format defined in `.feature-radar/base.md` → Classification Rules → `opportunities/`.

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
