# AI Context Router

This page is the in-repo manual for keeping the agent docs routed and true. It works without any skill installed. Load it with `python3 scripts/ai-context.py ai-context`.

Run `python3 scripts/ai-context.py --version` to identify the copied router's source release; no config is required. Updating the skill does not update this copy. Compare local customizations before replacing the script, and retain the repo's config and docs.

## Layers

1. **Kernel:** root `AGENTS.md`, loaded by every agent on every task. It holds only rules that every task needs, plus the one-line triggers that say which topic to load.
2. **Scoped instructions:** optional nested `AGENTS.md` files for one package or app. Map each to a topic, or add a reason-bearing `"unrouted"` exception when agents already load it by cwd.
3. **Topics:** the active config (`wiki/ai-context.json` by default, or the file selected by `AI_CONTEXT_CONFIG`) maps each topic to whole files or exact headings. `scripts/ai-context.py <topic>` prints only those sections.
4. **History:** `wiki/history/`, holding milestone logs in their original language. They are never loaded by default and are indexed in `wiki/README.md`.

The active config owns this root's local topics. The tables in `AGENTS.md` and `wiki/README.md` mirror those local topics. Mounted roots keep their own config, instructions and index; use `list` for the combined catalog.

## Shared installation (optional)

By default, copy the script to `scripts/ai-context.py`: the root is its parent's parent, and the config is `<root>/wiki/ai-context.json`. A symlink to that copy outside a `scripts/` directory, for example on PATH, uses the target's parent's parent when its own has no `wiki/ai-context.json` and `AI_CONTEXT_CONFIG` is unset. A shared script needs no local `scripts/` directory:

```sh
AI_CONTEXT_ROOT=/work/repo AI_CONTEXT_CONFIG=/work/settings/router.json \
  python3 /opt/tools/ai-context.py check
```

Use the same environment and script path for `list`, topic commands and CI/hooks; update commands in the kernel, this manual and the wiki index accordingly. When using an external config, replace their default config references with the selected path, including source-of-truth statements and topic-edit steps. `AI_CONTEXT_ROOT` alone uses that root's default config. `AI_CONTEXT_CONFIG` alone keeps the script-derived root. Empty or unset overrides use the defaults. Both selections are canonicalized; relative overrides resolve independently from invocation cwd, without tilde or shell-variable expansion by the script. Relative paths inside the config resolve from the selected root, even with an external config.

## Mount an existing contained router

To consume an independent router tree already inside the project, add this optional field to the active outer config:

```json
"mounts": {
  "kb": { "root": "modules/kb-core" }
}
```

The tree must already have its own config with a `topics` object, string descriptions and source lists, plus its own instructions and router index.

Each topic's `sources` is a list of objects with a nonempty `path` and optional string `heading` and booleans `frontmatter`, `stripFrontmatter` (default `false`). Optional path settings are nonempty strings, `indexed`/`skipDirs` are string lists, and `unrouted` is an object. Root/default/per-topic byte caps are nonnegative integers, excluding booleans. Ordinary unknown config fields remain accepted; unknown declaration fields do not.

Select it through the project router:

```sh
python3 scripts/ai-context.py list
python3 scripts/ai-context.py kb/guide
python3 scripts/ai-context.py build-deploy kb/guide
python3 scripts/ai-context.py check
```

The router reads data only: it neither acquires a module nor runs a script from it.

### Names and paths

- A mount declaration has required nonempty string `root`, optional nonempty string `config`, and no other fields. `config` defaults to `wiki/ai-context.json`; for another location use, for example, `"config": "context/router.json"`.
- Mount names are single nonempty segments: no slash, backslash, whitespace, control characters, `.` or `..`. A name reserves its entire `name/` prefix even when unavailable. A local `kb` can coexist with mount `kb`, but local `kb/guide` collides. Inner topic names may contain `/`; `kb/ops/guide` selects inner `ops/guide`.
- Relative mount roots resolve from the selected outer root, not cwd or the outer config's directory. Relative mount config paths and document paths resolve from the mounted root. Backslashes normalize to `/`; the router expands neither `~` nor environment variables.
- A mounted root must be a strict physical descendant of the outer root. Root-equal paths, prefix siblings and escaping symlinks fail. Config, instructions, sources, checked relative links and inventory scans stay physically inside their own root. Contained absolute paths and symlink aliases are accepted; config and content files must be regular files. Relative links retain each source's lexical directory, even for aliases to one physical file.
- Mounted configs may omit `mounts` or set it to `{}`. Nonempty inner mounts are rejected; declarations are never followed recursively. A mount root cannot contain the outer wiki or history directory, selected config or root instructions, and one mount root cannot be a strict ancestor of another. Two names for the same contained physical root are allowed and checked independently.

### Each root owns its checks

`list` keeps local rows first, then namespaced mounted rows in declaration/topic order, with origin such as `[modules/kb-core]`. Mounted source comments show outer-relative paths such as `<!-- modules/kb-core/wiki/guide.md -->`.

`check` visits the outer root and every available mount using each root's own `rootInstructions`, budgets, `wikiDir`, `historyDir`, `routerFile`, `indexed`, `skipDirs` and `unrouted`. Outer discovery tables never need to copy inner topics: the inner kernel names unqualified `guide`, and the caller selects `kb/guide`. Parent or sibling references, exceptions and budgets cannot satisfy an inner requirement. Change a mounted topic in its own config and local tables.

Topic byte caps measure the root's native render, including its native source comments, rather than the longer mounted display paths or combined invocation. Kernel counts retain unstripped UTF-8 text, including trailing whitespace.

Outer automatic orphan/indexed/wiki-link inventories exclude contained mounted physical trees and file/directory aliases, including modules under the outer wiki. A safely resolved root retains that ownership even when its config is invalid. Explicit outer sources and the explicit outer router file still get full ordinary checks. An outer relative link may enter a mount, but an inner relative link cannot escape to the outer project. External, absolute and fragment-only Markdown destinations retain their existing exclusions. Referenced indexed candidates still fail if outside the owner or not regular files.

### Failures and output

- A contained missing root produces one path-bearing `NOTICE mount kb: missing root ...` on `list` stdout; status is 0 if nothing else failed. `check` and a requested `kb/guide` fail for that missing root.
- Invalid declarations, collisions, outside roots, roots containing outer routing files or the outer wiki/history directories, ancestor/descendant mount roots, unreadable/missing/invalid configs, and nested mounts are errors. `list` reports them on stderr and continues healthy rows with status 1. `check` reports owner-qualified errors on stdout, continues other topics/roots and ends with one `ok` or `<N> root(s) failed`; each failing root counts once. Missing config is an error, not a missing-root notice.
- Topic calls load only selected mounted configs; an unavailable unrelated mount does not block a healthy request. Every requested name and body must succeed before any content prints. A late missing source, unknown topic, encoding/read failure or missing/duplicate heading leaves stdout empty, with status 1 and a requested-topic diagnostic on stderr. Topic rendering does not implicitly run `check`.
- Absent `mounts` and `"mounts": {}` preserve single-root behavior. `--version` stays config-free.

## When docs must change

Update docs **in the same change** that makes them stale:

| You did this | Update this |
|---|---|
| Changed behaviour a topic describes | That topic's page |
| Found a descriptive claim that contradicts code/tests | Verify and fix the stale description; report the evidence |
| Code conflicts with a hard limit, safety rule or intended requirement | Surface the conflict to the owner; do not weaken the rule to match code |
| Learned a lesson the hard way | Keep it in its topic; promote a one-line kernel rule only if every task needs it |
| Finished a milestone | Add `wiki/history/<milestone>.md` and one index row in `wiki/README.md` |
| Added a new kind of recurring task | Add a new topic: page, JSON entry, and both tables |
| Added a nested `AGENTS.md` | Map it in some topic, or record a reason-bearing exception if loaded by cwd |

Leave volatile state out of the docs: progress counts, who is doing what this week, today's blocker. Those belong in the tracker.

## Evidence and review

For consequential claims (safety, compatibility, limits or verification), keep a nearby source path/heading, test or decision reference, its revision/date when relevant, and status: observed, intended, inferred or unresolved. Distinguish a recorded test result from a current guarantee. Reuse existing evidence; no new metadata system is needed.

When a topic is incomplete, stale or contradictory, follow its source comments and inspect the relevant raw file, code, tests or decision. Load only what resolves the gap. Record unresolved conflicts rather than silently treating implementation as policy.

After a change, render the affected topics and review their claims against those sources. Check moved material for lost hard limits and missing task triggers. Review unchanged pages only when a changed claim depends on them; this is not a whole-wiki audit.

## Adding or changing a topic

1. Put the content in `wiki/<page>.md`. A topic should be a recognizable kind of work, not a single ticket or file.
2. Map it in the active config. Reference exact headings for large pages.
3. Add a row to this root's local topic tables in `AGENTS.md` and `wiki/README.md`; mounted topics belong to their owner's tables.
4. Run `python3 scripts/ai-context.py check`, then render the topic and read it as an agent would.

For a heading source, `"frontmatter": true` skips a closed leading envelope; default/false keeps legacy behavior. First line must be `---` (optional BOM); closure is column-zero `---` or `...`. Trailing spaces/tabs are allowed. No YAML validation occurs. No closer means legacy headings. Whole-file output is unchanged unless `stripFrontmatter` (source, or top-level default; source wins) is true: it drops a closed leading envelope from output and budgets and makes headings frontmatter-aware. Sections add no metadata. Detection reads delimiters only: a page starting `---`, `Intro`, `---` (a rule, then a setext heading) loses `Intro`. Under a top-level default, give such a page `"stripFrontmatter": false`.

## What check enforces

- Every configured content path stays inside its owning root and exists, and every heading matches exactly once.
- Relative Markdown links and images resolve from their containing page to files inside the repo, including after symlink resolution. This is always checked in complete routed sources, every wiki Markdown page (the router index, history and `"unrouted"` exceptions included), and `.md` pages matched by optional `indexed` patterns.
- Nested and multiline inline destinations and used reference definitions are checked; reference errors point to the definition line. Unused definitions, fenced/indented/inline code, HTML comments/raw HTML, escaped markup, external URLs, absolute paths and fragment-only links are skipped. Markdown escapes and HTML entities are decoded before removing queries/fragments and percent-decoding filenames. Heading fragments are not validated.
- `AGENTS.md` and every topic stay under their byte budgets. Over budget means split the topic. Do not raise the cap.
- Every topic is listed in its own root instructions (`AGENTS.md` by default).
- **No orphans:**
  - every `wiki/` page (history excluded) is loaded by some topic;
  - every history file is indexed in `wiki/README.md`;
  - every nested `AGENTS.md` is loaded by some topic.

  A deliberate exception goes under `"unrouted"` in the JSON, with a reason, including scoped instructions agents already load by cwd. Keys accept exact paths or case-sensitive fnmatch globs; backslashes normalize to `/`. For example, `"projects/*/AGENTS.md": "Loaded by cwd."` matches both `projects/api/AGENTS.md` and `projects/team/api/AGENTS.md`: `*` crosses `/`, and `**` has no special recursive meaning. `?` and bracket classes also work. Keys match themselves and also act as patterns, regardless of file existence: `wiki/file[1].md` exempts both itself and `wiki/file1.md`. Use `wiki/file[[]1].md` to exempt the literal bracketed filename without also exempting `wiki/file1.md`. Unmatched orphans still fail.

Optional `"indexed"` patterns (a list of strings, default `[]`) check discovery of `.md` pages across repo directories, including hidden, dependency, and build directories but excluding `.git` metadata, for example `"indexed": ["projects/*/*-runbook.md"]`. Directory symlinks are not followed; patterns and references use real repo-relative paths, and files in real directories are inspected once without alias traversal. Use forward-slash repo-relative patterns. Python `fnmatch` lets `*` cross `/`; matching is case-sensitive on POSIX and follows platform normalization on Windows.

An indexed page must be a topic source, including a heading-selected source, or have its full repo-relative path named in root instructions, the configured router file, or a topic's successfully rendered text. Only selected sections count, and a basename or relative link without the full string does not. Fix a failure by naming the path in a topic page, routing the page as a source, or listing an exact path or matching case-sensitive glob under `"unrouted"` with a nonblank string reason. If multiple exceptions match, any nonblank string reason exempts the page from the indexed check. Blank or non-string reasons still exempt legacy orphans, but do not satisfy an indexed check. These references do not exempt pages from the existing wiki, history, or nested-instructions rules.

Optional `"skipDirs"` (a list of strings, default `[]`) keeps `check` out of bulky trees that hold no instructions, such as generated output or evidence dumps: exact repo-relative directory paths or case-sensitive fnmatch globs, matched like `"unrouted"` keys. Pages inside a skipped directory are checked only when a topic routes them or the path is the explicit router file. The owner's wiki is always walked except for mounted trees, which get their own checks as described above.

`check` runs in CI to catch structural drift. Passing does not establish factual accuracy, policy compliance, freshness or complete task coverage; the targeted review above is still needed.

## Combining topics

`python3 scripts/ai-context.py --dedupe a b` prints each identical source entry (same root, path, heading and options) once, under its first topic. Every source is still validated; single-topic output and `check` budgets are unchanged. A local topic named `--dedupe` takes precedence.

## Skills

Skills are workflow adapters. They may call `ai-context.py`, run checks and shorten steps, but no rule may live only in a skill. With no skill installed, this page and the kernel must still be enough.
