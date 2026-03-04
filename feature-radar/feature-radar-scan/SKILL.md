---
name: feature-radar-scan
description: |
  Discover new feature opportunities from multiple sources — creative brainstorming,
  user feedback, ecosystem evolution, technical possibilities, and cross-project research —
  and add them to .feature-radar/opportunities/. Use this when the user wants to generate
  NEW ideas rather than evaluate existing ones. Even casual mentions like "I wonder what else
  we could do" or "let's think about new features" should trigger this skill.
  Use when:
  - Brainstorming creative feature ideas or exploring new directions
  - User says "what else could we build?" or "give me some ideas"
  - Reviewing user feedback, GitHub issues, or community requests for unmet needs
  - Exploring adjacent tools and ecosystems for inspiration
  - Periodic opportunity refresh to keep the backlog current
  Trigger phrases: "scan opportunities", "find new features", "brainstorm ideas",
  "what could we build", "refresh opportunities", "scan ecosystem", "give me feature ideas",
  "what are we missing", "explore new directions"
---

# Scan Opportunities

Discover new feature opportunities and add them to `.feature-radar/opportunities/`.

## Deep Read

<HARD-GATE>
Read and follow `reference/DEEP-READ.md` — complete all 6 steps before proceeding.
</HARD-GATE>

## Behavioral Directives

<HARD-GATE>
Read and follow `reference/DIRECTIVES.md`.

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
7. **Checkpoint — Review & Annotate** per `reference/WORKFLOW-PATTERNS.md`

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

Follow the template in `reference/DIRECTIVES.md`, with skill name "Scan Complete".
