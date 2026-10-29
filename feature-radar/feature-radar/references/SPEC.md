# Feature Radar Data Specification

**Status**: v1

**Purpose**: Define the `.feature-radar/` data format so any AI tool can produce and consume feature radar data without reading SKILL.md files.

## 1. Overview

`.feature-radar/` is a project-local directory that stores structured feature tracking data — what exists, what's planned, what was tried, and what the ecosystem looks like. All files are Markdown with inline key-value metadata. No special tooling is required beyond a filesystem and a Markdown parser.

## 2. Directory Structure

```
.feature-radar/
├── base.md                        # REQUIRED — project context + classification rules
├── archive/                       # REQUIRED dir — terminal-state features
│   └── {nn}-{slug}.md
├── opportunities/                 # REQUIRED dir — open features not yet implemented
│   └── {nn}-{slug}.md
├── specs/                         # REQUIRED dir — cross-cutting knowledge
│   └── {topic}.md
└── references/                    # REQUIRED dir — external observations
    └── {topic}.md
```

All four subdirectories MUST exist, even if empty.

## 3. File Formats

### 3.1 base.md

The root document. Describes the project and defines classification rules.

**Required sections** (in order):

| Section | Purpose |
|---------|---------|
| Project Context | Language, Architecture, Key Feature Areas, Core Philosophy, Inspiration Sources |
| Feature Inventory | Implemented Features table + Value & Innovation Landscape table |
| Tracking Summary | Counts per category (see table format below) |
| Directory Layout | Visual tree of `.feature-radar/` |
| Classification Rules | Definitions for archive/, opportunities/, specs/, references/ |
| Maintenance Workflow | How features flow between directories |
| Archive Extraction Checklist | 5-check checklist (see section 4.3) |

**Tracking Summary table format:**

```markdown
| Category | Count | Description |
|----------|-------|-------------|
| archive/ | {n} | Completed, covered, rejected, or deferred features |
| opportunities/ | {n} | Open features not yet implemented |
| specs/ | {n} | Cross-cutting patterns and architectural decisions |
| references/ | {n} | External observations, inspiration, and ecosystem analysis |
```

Counts MUST reflect the actual number of files in each directory.

**Feature Inventory — Implemented Features table:**

```markdown
| Feature | Code Path | Docs Coverage |
|---------|-----------|---------------|
| {feature} | {path} | {✓ documented / ✗ undocumented} |
```

**Feature Inventory — Value & Innovation Landscape table:**

```markdown
| Capability | Current State | Best-in-Class Reference | Opportunity |
|------------|---------------|------------------------|-------------|
| {capability} | {✓/✗/partial} | {who does it well} | {room for improvement or innovation} |
```

### 3.2 archive/{nn}-{slug}.md

A feature in terminal state.

**Filename**: `{nn}-{slug}.md` where `{nn}` is a zero-padded two-digit sequential number and `{slug}` is a lowercase kebab-case identifier.

**Template:**

```markdown
# {nn}. {Feature Name}

**Status**: {status}
**Ref**: {upstream issue/PR links, if any}
**Implemented**: {code paths / commits, if Done}

## Description
{What the feature does and why it was requested}

## Implementation Notes
{Key decisions, trade-offs, and anything future maintainers should know}
```

**Fields:**

| Field | Required | Values |
|-------|----------|--------|
| Status | YES | `Done` \| `Covered` \| `Rejected` \| `N/A` \| `Deferred` |
| Ref | NO | URL(s) to issues, PRs, or external references |
| Implemented | NO | Code paths or commit references (expected when Status is `Done`) |

**Status enum definitions:**

- **Done** — fully implemented and working
- **Covered** — existing functionality already handles the use case
- **Rejected** — decided against implementing
- **N/A** — not applicable to the project's architecture
- **Deferred** — valuable but postponed; MUST include rationale and re-evaluation conditions

### 3.3 opportunities/{nn}-{slug}.md

An open feature not yet implemented.

**Filename**: Same convention as archive — `{nn}-{slug}.md`.

**Template:**

```markdown
# {nn}. {Feature Name}

**Status**: {status}
**Impact**: {impact}
**Effort**: {effort}
**Ref**: {upstream issue/PR links, if any}

## Description
{What the feature does and the problem it solves}

## Design Notes
{Implementation considerations, architectural constraints, dependencies}

## Our Position
{Honest assessment — do we actually want this? Why or why not?}
```

**Fields:**

| Field | Required | Values |
|-------|----------|--------|
| Status | YES | `Open` \| `Partially Done` \| `Low Priority` |
| Impact | YES | `High` \| `Medium` \| `Low` |
| Effort | YES | `Low` \| `Medium` \| `High` |
| Ref | NO | URL(s) to issues, PRs, or external references |

**Effort guidelines:**

- **Low** — less than 1 day
- **Medium** — 1-3 days
- **High** — 1+ week

### 3.4 specs/{topic}.md

Cross-cutting knowledge: patterns, decisions, pitfalls, techniques.

**Filename**: `{topic}.md` — named by the pattern/concept, NOT by the feature that produced it. Examples: `yaml-config-merge.md`, `symlink-vs-copy-tradeoffs.md`. Counterexamples (bad): `audit-feature-learnings.md`, `v2-refactor-notes.md`.

**Template:**

```markdown
# {Topic}

## Context
{What was being built or solved}

## {Classification}
{The reusable knowledge — this section heading matches the classification type}

## Why It Matters
{When future work would benefit from this}
```

**Classification** (exactly one per file):

| Type | Definition |
|------|-----------|
| Pattern | Recurring solution worth replicating |
| Decision | Architectural choice with rationale |
| Pitfall | Mistake or dead end to avoid |
| Technique | Implementation approach that worked well |

The second section heading MUST be one of: `## Pattern`, `## Decision`, `## Pitfall`, `## Technique`.

One topic per file. If a learning spans multiple topics, create multiple files. Append to an existing file when new learning extends a known topic.

### 3.5 references/{topic}.md

External observations, inspiration, ecosystem trends, and research findings.

**Filename**: `{topic}.md` — named by the subject being tracked, NOT by the event. Examples: `vercel-skills-ecosystem.md`, `agent-path-conventions.md`, `cli-ux-patterns.md`. Counterexamples (bad): `2026-02-18-update.md`, `interesting-finding.md`.

**Template:**

```markdown
# {Topic}

> {One-line summary of what this reference tracks}

## {Date} — {Entry Title}

**Source**: {URL}

{What happened and why it matters to us}

**Implications**:
- {What this means for our project}
```

**Structure rules:**

- Each file tracks a **subject** (e.g., a project, a pattern, an ecosystem trend)
- New observations are appended chronologically as new `## {Date} — {Entry Title}` sections
- Do NOT create a new file per observation — append to the existing subject file
- Always include source URL and date for traceability
- Date format: `YYYY-MM-DD`

## 4. Lifecycle

### 4.1 Status Transitions

```
opportunities/              archive/
┌─────────────┐            ┌─────────────┐
│ Open        │───────────→│ Done        │
│ Partially   │            │ Covered     │
│   Done      │            │ Rejected    │
│ Low Priority│            │ N/A         │
└─────────────┘            │ Deferred    │
                           └─────────────┘
```

- Features flow from `opportunities/` to `archive/` when they reach a terminal state.
- Features may also be created directly in `archive/` if already resolved at discovery time.
- `Deferred` items MUST be periodically re-evaluated. "Deferred" is not permanent — include rationale and conditions for re-evaluation.

### 4.2 Numbering

- `{nn}` is a sequential number shared across `opportunities/` and `archive/`.
- Numbers are zero-padded to two digits (e.g., `01`, `02`, ... `99`).
- When archiving from `opportunities/`, **keep the same number**. The file moves; the number does not change.
- New items receive the next number after the highest existing number across both directories.

### 4.3 Archive Extraction Contract

Every time an opportunity moves to `archive/`, ALL 5 checks MUST be performed:

```
□ archive/{nn}-{slug}.md created with correct status
□ Extract learnings      → specs/{topic}.md (create or append)
□ Derive new opportunities → opportunities/{nn}-{slug}.md (create if found)
□ Update references       → references/{topic}.md (update if relevant)
□ Update ecosystem trends → specs/ecosystem-trends.md (update if relevant)
```

Each check requires an explicit finding. Acceptable responses:

- "No learnings to extract"
- "New opportunity identified: {description}" (create the file)
- "No reference updates needed"
- "No ecosystem trend changes"

Skipping any check without a stated finding is a spec violation.

## 5. Reconciliation

To verify state consistency, perform:

**Count verification:**

1. Count actual files in `archive/`, `opportunities/`, `specs/`, `references/`
2. Compare with counts in `base.md` Tracking Summary table
3. If mismatch: update `base.md` counts

**Extraction audit:**

1. For each file in `archive/`, verify the extraction checklist was completed
2. Missing extractions (no corresponding specs/, no derived opportunities noted) indicate incomplete archival

## 6. Interoperability

- All files are plain Markdown (`.md`)
- Metadata uses inline bold key-value pairs (`**Key**: Value`), not YAML frontmatter
- No special tooling required — readable and writable with any text editor or Markdown parser
- To programmatically parse metadata, match lines of the form `**{Key}**: {Value}`
- File discovery: list directory contents; filenames encode the numbering and slug
- The format is designed for AI tools that operate on filesystems and produce/consume Markdown
