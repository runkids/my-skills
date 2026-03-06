---
name: feature-radar
description: |
  Full-cycle feature discovery, evaluation, and prioritization. Analyzes the codebase, builds
  a knowledge base at .feature-radar/, and runs a 6-phase workflow to recommend what to build next.
  Use when:
  - "what should we build next?" or "what's most impactful?"
  - Review/prioritize backlog or feature ideas
  - Set up feature tracking for a new project
  - Periodic review to reassess priorities and find gaps
  - Evaluate trade-offs between multiple feature ideas
  - Roadmap planning, project direction, strategic priorities
  - Identifying documentation gaps
  Trigger phrases: "feature radar", "what should we build next", "feature priorities",
  "project roadmap", "help me prioritize", "review our backlog", "innovation scan"
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

1. **Detect stack** — read `go.mod`, `package.json`, `Cargo.toml`, `pyproject.toml`. Follow imports to understand the dependency graph. Don't just read the config — understand the architecture.
2. **Map structure** — list top-level directories. For each, read at least one file to understand its purpose. Identify: entry points, core logic, tests, docs, configuration.
3. **Extract features** — scan exports, commands, API routes, or public functions. Read the implementations, not just the names. Understand what each feature actually does.
4. **Find inspiration sources** — read README, CONTRIBUTING, docs/ for related projects and communities
5. **Verify with user** — present the generated base.md and ask: "Does this accurately describe your project?"
</HARD-GATE>

After presenting base.md, support iterative refinement per `reference/WORKFLOW-PATTERNS.md`.

<HARD-GATE>
Do NOT proceed to the Workflow until the user approves base.md.
</HARD-GATE>

### base.md Template

Generate `base.md` following the structure defined in `SPEC.md` (sections 2-5).
Read `SPEC.md` first, then fill `{placeholders}` with project-specific analysis.

Key sections to generate:
- **Project Context** — detected language, architecture, key feature areas, core philosophy, inspiration sources
- **Feature Inventory** — implemented features table + value & innovation landscape table
- **Tracking Summary** — counts per category (start at 0)
- **Directory Layout** — tree view
- **Classification Rules** — per SPEC.md §3.2-3.5
- **Maintenance Workflow** — feature flow between directories
- **Archive Extraction Checklist** — per SPEC.md §4.3

After creating the directory, ask the user:
**"Should I add `.feature-radar/` to `.gitignore`?"**
(Recommended if the tracking data is internal and shouldn't be committed.)

## Subsequent Runs

On subsequent runs (`.feature-radar/` already exists):
1. Read existing `base.md` — do NOT overwrite
2. Run reconciliation per `reference/DEEP-READ.md` steps 4-6
3. Proceed to Workflow Phase 1

## Behavioral Directives

<HARD-GATE>
Read and follow `reference/DIRECTIVES.md`.

Additional directives for this skill:
- **Do not skip phases** — Phase 1-3 are mandatory. For Phase 4-6, state the skip condition check result before deciding to skip.
- **Reconcile on subsequent runs** — see "Subsequent Runs" section above.
</HARD-GATE>

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

**Checkpoint**: State classification results — how many archived, how many open, how many specs, how many references. Ask: "Phase 1 complete: {summary}. Continue to Phase 2?"

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

**Checkpoint**: List all opportunity files created with Impact/Effort ratings. Ask: "Phase 3 complete: {n} opportunities organized. Continue to Phase 4?"

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

**Checkpoint**: Present the tier ranking table. Ask: "Phase 5 complete: ranking above. Continue to Phase 6 (Propose)?"

### Phase 6: Propose & Decide

1. Present **top 1-3 "Build next" features** with:
   - One-paragraph pitch: what value does it create?
   - Estimated effort (days, not hours)
   - Key decisions to make
2. Ask: **"Should we enter plan mode for [feature]?"**

## Completion Summary

Follow the template in `reference/DIRECTIVES.md`, with skill name "Complete" and an additional line:
`Top recommendation: {feature name} — {one-line pitch}`

## Guardrails

- **Don't copy blindly.** Evaluate fit with YOUR architecture and users, not someone else's.
- **Don't overcount.** 1 issue with no comments = weak signal.
- **Don't undercount.** Multiple independent asks = strong signal.
- **Chase value, not features.** Ask "what problem does this solve?" before "what does this do?"
- **Be honest about effort.** Low < 1 day. Medium 1-3 days. High 1+ week.
- **Challenge deferred items.** "Deferred" ≠ "forever" — re-evaluate each session.
- **Think creatively.** The best features aren't always the obvious ones — look for novel angles.
