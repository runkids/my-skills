---
name: feature-radar
description: |
  Discover, evaluate, and prioritize feature opportunities from any source — creative ideation,
  user pain points, ecosystem trends, technical breakthroughs, or cross-project research.
  Use when:
  - Brainstorming new feature ideas or exploring innovation directions
  - Reviewing feature opportunities against existing codebase to find completed or covered features
  - Archiving resolved features with mandatory learning extraction
  - Organizing open opportunities, cross-cutting specs, or external references
  - Identifying documentation gaps (implemented features missing from docs/website)
  - Evaluating feature value and prioritizing what to build next
  - Proposing the highest-impact feature to push the project forward
  Trigger phrases: "feature radar", "check feature status", "what should we build next",
  "feature ideas", "feature priorities", "update opportunities", "innovation scan"
---

# Feature Discovery & Prioritization

## Bootstrap (First Run)

If `.feature-radar/` does not exist at the project root, create it:

```
.feature-radar/
├── base.md
├── archive/
├── opportunities/
├── specs/
└── references/
```

Then generate `base.md` by completing the following:

<HARD-GATE>
Complete ALL steps before presenting base.md to the user:

1. **Detect stack** — read `go.mod`, `package.json`, `Cargo.toml`, `pyproject.toml`
2. **Map structure** — list top-level directories, identify: entry points, core logic, tests, docs
3. **Extract features** — scan exports, commands, API routes, or public functions to build Feature Inventory
4. **Find inspiration sources** — read README, CONTRIBUTING, docs/ for related projects and communities
5. **Verify with user** — present the generated base.md and ask: "Does this accurately describe your project?"
</HARD-GATE>

### base.md Template

Generate the following, filling `{placeholders}` with project-specific analysis:

```markdown
# Feature Radar — {Project Name}

## Project Context

- **Language**: {detected from go.mod / package.json / Cargo.toml / pyproject.toml}
- **Architecture**: {key directories and their purpose, e.g. "cmd/ (CLI), internal/ (core logic), ui/ (frontend)"}
- **Key Feature Areas**: {main capability domains, e.g. "install, sync, audit, search, backup"}
- **Core Philosophy**: {what makes this project different, e.g. "local-first, cross-platform, symlink-based"}
- **Inspiration Sources**: {related projects, communities, and ecosystems to watch — e.g. "vercel-labs/skills, npm ecosystem, AI agent tools"}

## Feature Inventory

### Implemented Features
{Scan codebase and list existing features with their code locations}

| Feature | Code Path | Docs Coverage |
|---------|-----------|---------------|
| {feature} | {path} | {✓ documented / ✗ undocumented} |

### Value & Innovation Landscape
{Compare current capabilities with industry best practices and emerging possibilities}

| Capability | Current State | Best-in-Class Reference | Opportunity |
|------------|---------------|------------------------|-------------|
| {capability} | {✓/✗/partial} | {who does it well} | {room for improvement or innovation} |

## Tracking Summary

| Category | Count | Description |
|----------|-------|-------------|
| archive/ | {n} | Completed, covered, rejected, or deferred features |
| opportunities/ | {n} | Open features not yet implemented |
| specs/ | {n} | Cross-cutting patterns and architectural decisions |
| references/ | {n} | External observations, inspiration, and ecosystem analysis |

## Directory Layout

.feature-radar/
├── base.md          ← This file: project context + classification rules
├── archive/         ← Done / Covered / Rejected / N/A features
│   └── {nn}-{slug}.md
├── opportunities/   ← Open features not yet implemented
│   └── {nn}-{slug}.md
├── specs/           ← Cross-cutting knowledge & architectural decisions
│   └── {topic}.md
└── references/      ← External inspiration, ecosystem observations & research
    └── {topic}.md

## Classification Rules

### 1. archive/ — Terminal State

Features that shipped, are covered by existing work, rejected, not applicable, or deferred.

Naming: `{nn}-{slug}.md`

File template:
- **Status**: Done | Covered | Rejected | N/A | Deferred
- **Ref**: upstream issue/PR links
- **Implemented**: code paths / commits
- Sections: Description, Implementation Notes

### 2. opportunities/ — Open

Features not yet implemented but still valuable.

Naming: `{nn}-{slug}.md`

File template:
- **Status**: Open | Partially Done | Low Priority
- **Impact**: High | Medium | Low
- **Effort**: Low | Medium | High
- **Ref**: upstream issue/PR links
- Sections: Description, Design Notes, Our Position

### 3. specs/ — Cross-Cutting Knowledge

Patterns, architectural decisions, unique strengths — not tied to a single feature.

Naming: `{topic}.md` — updated incrementally as new insights emerge.

### 4. references/ — External

Ecosystem observations, creative inspiration, research findings, and cross-project learnings.

Naming: `{topic}.md` — cite original URLs and dates for traceability.

## Maintenance Workflow

New feature request       → create opportunities/{nn}-{slug}.md
Feature completed         → move to archive/ + run extraction checklist
New pattern discovered    → write to specs/
External observation      → write to references/
Periodic review           → re-evaluate Deferred items in archive/

## Archive Extraction Checklist (Mandatory)

Every time an opportunity moves to archive/, perform ALL checks:

1. **Extract learnings** — reusable patterns, architectural decisions, pitfalls
   → write to specs/{topic}.md (create or append)

2. **Derive new opportunities** — did the implementation reveal new needs?
   → create opportunities/{nn}-{slug}.md

3. **Update references** — new external observations or ecosystem context?
   → update references/{topic}.md

4. **Update ecosystem trends** — broader industry shift?
   → update specs/ecosystem-trends.md

□ archive/{nn}-{slug}.md created with correct status
□ Check for extractable learnings      → specs/
□ Check for derived new opportunities  → opportunities/
□ Check for new external references    → references/
□ Check if ecosystem trends changed    → specs/ecosystem-trends.md
```

After creating the directory, ask the user:
**"Should I add `.feature-radar/` to `.gitignore`?"**
(Recommended if the tracking data is internal and shouldn't be committed.)

On subsequent runs, read existing `base.md` — do not overwrite.

## Workflow

Execute phases in order.

<HARD-GATE>
Phase execution rules:
- **Phase 1-3**: ALWAYS execute. These are mandatory.
- **Phase 4** (Gap Analysis): Skip ONLY if no documentation directory exists in the project.
- **Phase 5-6** (Evaluate & Propose): Skip ONLY if no open opportunities exist in `.feature-radar/opportunities/`.

For each phase completed, state what was produced before moving to the next phase.
</HARD-GATE>

### Phase 1: Scan & Classify

1. Read source files (feature ideas, user feedback, ecosystem observations, creative proposals, issue trackers)
2. Cross-reference each entry against the codebase
3. Classify:
   - **Done / Covered / Rejected / N/A** → archive
   - **Open / Partially Done** → opportunity
   - **Cross-cutting pattern** → specs
   - **External observation** → references

### Phase 2: Archive Completed Features

For each archive candidate:

1. Create `archive/{nn}-{slug}.md`
2. Run the **Archive Extraction Checklist** (mandatory):
   - Extract learnings → `specs/`
   - Derive new opportunities → `opportunities/`
   - Update references → `references/`
   - Update ecosystem trends → `specs/ecosystem-trends.md`
3. Mark the entry as processed in the source (strikethrough + status)

### Phase 3: Organize Open Opportunities

1. Create `opportunities/{nn}-{slug}.md`
2. Assess **Impact** and **Effort** realistically
3. Write an honest "Our Position" — do we actually want this?

### Phase 4: Gap Analysis

Find implemented features that docs don't mention:

1. Scan documentation for coverage of implemented features
2. For each gap: which feature, which page should cover it, standalone guide or section

### Phase 5: Evaluate & Prioritize

| Criterion | Question |
|-----------|----------|
| **Real user demand** | Are users actually asking for this? |
| **Value uplift** | Does this meaningfully improve the user experience or unlock new possibilities? |
| **Innovation potential** | Does this introduce a creative breakthrough or unique approach? |
| **Effort / impact ratio** | Is the cost justified by the benefit? |
| **Architectural fit** | Does it align with our core philosophy? |
| **Ecosystem timing** | Is the ecosystem ready? |

Rank into tiers:
- **Build next**: High value + strong demand or innovation potential + reasonable effort
- **Build soon**: Good value + moderate demand
- **Monitor**: Low demand or premature
- **Skip**: Conflicts with philosophy or negligible value

### Phase 6: Propose & Decide

1. Present **top 1-3 "Build next" features** with:
   - One-paragraph pitch: what value does it create?
   - Estimated effort (days, not hours)
   - Key decisions to make
2. Ask: **"Should we enter plan mode for [feature]?"**

## Guardrails

- **Don't copy blindly.** Evaluate fit with YOUR architecture and users, not someone else's.
- **Don't overcount.** 1 issue with no comments = weak signal.
- **Don't undercount.** Multiple independent asks = strong signal.
- **Chase value, not features.** Ask "what problem does this solve?" before "what does this do?"
- **Be honest about effort.** Low < 1 day. Medium 1-3 days. High 1+ week.
- **Challenge deferred items.** "Deferred" ≠ "forever" — re-evaluate each session.
- **Think creatively.** The best features aren't always the obvious ones — look for novel angles.
