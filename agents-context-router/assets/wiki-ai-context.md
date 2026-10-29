# AI Context Router

This page is the in-repo manual for keeping the agent docs routed and true. It works without any skill installed. Load it with `python3 scripts/ai-context.py ai-context`.

Run `python3 scripts/ai-context.py --version` to identify the copied router's source release; no config is required. Updating the skill does not update this copy. Compare local customizations before replacing the script, and retain the repo's config and docs.

## Layers

1. **Kernel:** root `AGENTS.md`, loaded by every agent on every task. It holds only rules that every task needs, plus the one-line triggers that say which topic to load.
2. **Scoped instructions:** optional nested `AGENTS.md` files for one package or app. Map each to a topic, or add a reason-bearing `"unrouted"` exception when agents already load it by cwd.
3. **Topics:** the active config (`wiki/ai-context.json` by default, or the file selected by `AI_CONTEXT_CONFIG`) maps each topic to whole files or exact headings. `scripts/ai-context.py <topic>` prints only those sections.
4. **History:** `wiki/history/`, holding milestone logs in their original language. They are never loaded by default and are indexed in `wiki/README.md`.

The active config is the single source of truth: `<root>/wiki/ai-context.json` by default, or the file selected by `AI_CONTEXT_CONFIG`. The tables in `AGENTS.md` and `wiki/README.md` mirror it for discovery.

## Shared installation (optional)

By default, copy the script to `scripts/ai-context.py`: the root is its parent's parent, and the config is `<root>/wiki/ai-context.json`. A symlink to that copy outside a `scripts/` directory, for example on PATH, uses the target's parent's parent when its own has no `wiki/ai-context.json` and `AI_CONTEXT_CONFIG` is unset. A shared script needs no local `scripts/` directory:

```sh
AI_CONTEXT_ROOT=/work/repo AI_CONTEXT_CONFIG=/work/settings/router.json \
  python3 /opt/tools/ai-context.py check
```

Use the same environment and script path for `list`, topic commands and CI/hooks; update commands in the kernel, this manual and the wiki index accordingly. When using an external config, replace their default config references with the selected path, including source-of-truth statements and topic-edit steps. `AI_CONTEXT_ROOT` alone uses that root's default config. `AI_CONTEXT_CONFIG` alone keeps the script-derived root. Empty or unset overrides use the defaults. Both selections are canonicalized; relative overrides resolve independently from invocation cwd, without tilde or shell-variable expansion by the script. Relative paths inside the config resolve from the selected root, even with an external config.

## When docs must change

Update docs **in the same change** that makes them stale:

| You did this | Update this |
|---|---|
| Changed behaviour a topic describes | That topic's page |
| Found a doc that contradicts the code | Fix the doc, because the code wins; mention it in your handoff |
| Learned a lesson the hard way | A one-line kernel rule plus the procedure in its topic |
| Finished a milestone | Add `wiki/history/<milestone>.md` and one index row in `wiki/README.md` |
| Added a new kind of recurring task | Add a new topic: page, JSON entry, and both tables |
| Added a nested `AGENTS.md` | Map it in some topic, or record a reason-bearing exception if loaded by cwd |

Leave volatile state out of the docs: progress counts, who is doing what this week, today's blocker. Those belong in the tracker.

## Adding or changing a topic

1. Put the content in `wiki/<page>.md`. A topic should be a recognizable kind of work, not a single ticket or file.
2. Map it in the active config: `<root>/wiki/ai-context.json` by default, or the file selected by `AI_CONTEXT_CONFIG`. Reference exact headings for large pages.
3. Add a row to the topic tables in `AGENTS.md` and `wiki/README.md`.
4. Run `python3 scripts/ai-context.py check`, then render the topic and read it as an agent would.

## What check enforces

- Every path stays inside the repo and exists, and every heading matches exactly once.
- Relative Markdown links and images resolve from their containing page to files inside the repo, including after symlink resolution. This is always checked in complete routed sources, every wiki Markdown page (the router index, history and `"unrouted"` exceptions included), and `.md` pages matched by optional `indexed` patterns.
- Nested and multiline inline destinations and used reference definitions are checked; reference errors point to the definition line. Unused definitions, fenced/indented/inline code, HTML comments/raw HTML, escaped markup, external URLs, absolute paths and fragment-only links are skipped. Markdown escapes and HTML entities are decoded before removing queries/fragments and percent-decoding filenames. Heading fragments are not validated.
- `AGENTS.md` and every topic stay under their byte budgets. Over budget means split the topic. Do not raise the cap.
- Every topic is listed in `AGENTS.md`.
- **No orphans:**
  - every `wiki/` page (history excluded) is loaded by some topic;
  - every history file is indexed in `wiki/README.md`;
  - every nested `AGENTS.md` is loaded by some topic.

  A deliberate exception goes under `"unrouted"` in the JSON, with a reason, including scoped instructions agents already load by cwd. Keys accept exact paths or case-sensitive fnmatch globs; backslashes normalize to `/`. For example, `"projects/*/AGENTS.md": "Loaded by cwd."` matches both `projects/api/AGENTS.md` and `projects/team/api/AGENTS.md`: `*` crosses `/`, and `**` has no special recursive meaning. `?` and bracket classes also work. Keys match themselves and also act as patterns, regardless of file existence: `wiki/file[1].md` exempts both itself and `wiki/file1.md`. Use `wiki/file[[]1].md` to exempt the literal bracketed filename without also exempting `wiki/file1.md`. Unmatched orphans still fail.

Optional `"indexed"` patterns (a list of strings, default `[]`) check discovery of `.md` pages across repo directories, including hidden, dependency, and build directories but excluding `.git` metadata, for example `"indexed": ["projects/*/*-runbook.md"]`. Directory symlinks are not followed; patterns and references use real repo-relative paths, and files in real directories are inspected once without alias traversal. Use forward-slash repo-relative patterns. Python `fnmatch` lets `*` cross `/`; matching is case-sensitive on POSIX and follows platform normalization on Windows.

An indexed page must be a topic source, including a heading-selected source, or have its full repo-relative path named in root instructions, the configured router file, or a topic's successfully rendered text. Only selected sections count, and a basename or relative link without the full string does not. Fix a failure by naming the path in a topic page, routing the page as a source, or listing an exact path or matching case-sensitive glob under `"unrouted"` with a nonblank string reason. If multiple exceptions match, any nonblank string reason exempts the page from the indexed check. Blank or non-string reasons still exempt legacy orphans, but do not satisfy an indexed check. These references do not exempt pages from the existing wiki, history, or nested-instructions rules.

`check` runs in CI, so drift fails the build instead of rotting quietly.

## Skills

Skills are workflow adapters. They may call `ai-context.py`, run checks and shorten steps, but no rule may live only in a skill. With no skill installed, this page and the kernel must still be enough.
