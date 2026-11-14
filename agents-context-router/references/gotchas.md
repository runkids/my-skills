# Gotchas

Each item below is a trap that makes a split lose content or route agents to the wrong text. Each one says why it matters.

## Content

1. **Keep "every task" and "important" apart.** The kernel test is whether an agent would do something wrong on an unrelated task without this line. Important but task-specific text, like the whole debugging runbook, belongs in a topic. The kernel keeps only the one-line trigger: "if every job fails the same way, suspect our code; load `debugging`". Without the trigger, the agent never loads the topic.

2. **Promote lessons selectively, not automatically.** Keep task-specific lessons and procedures in their topic. Only a lesson needed on every task becomes a one-line kernel rule; importance alone is not enough. The incident write-up goes to history, with evidence preserved.

3. **Move verbatim first, edit second.** Rewriting while moving is how paragraphs vanish. Move whole sections into the history and topic pages in the original language. Then prune duplicates in a separate pass, and compare total bytes against the backup at the end.

4. **Keep history in its original language.** Milestone logs are the evidence trail for humans, so translating them adds risk and helps nobody. Instruction pages that agents read can be English. Human docs can stay in the team's language. State the language rules once, in the kernel.

5. **Leave volatile state out of the docs.** Progress counts, "currently running batch", today's blocker: these belong in a state file or the tracker. A doc that says "7 of 256 done" is wrong by tomorrow and misleads the next agent.

6. **Let a history section be an operating manual when it really is one.** Sometimes a milestone log's "Usage" or "Safety" section is the only precise description of a tool. Do not duplicate it. Reference its exact heading from the topic.

## Routing

7. **Route topics by task, not by file.** "calibration", "debugging" and "export" beat "architecture.md part 2". The agent chooses by what it is about to do. Put a single "use when…" line on each topic.

8. **One topic per task by default.** Say so in the kernel: "pick the single closest topic; load a second only when the task crosses two seams." Otherwise agents load everything "to be safe" and the split buys nothing.

9. **Each root's JSON owns its local topics. Its tables are mirrors.** `wiki/ai-context.json` decides what loads for that root. The local tables in `AGENTS.md` and `wiki/README.md` provide discovery; `check` fails when an own topic is missing from its kernel. Use `list` for mounted names such as `kb/guide`; keep unqualified `guide` in the inner kernel, not the outer tables.

10. **Prefer exact headings to line ranges.** Line numbers break on every edit. A heading reference survives edits, and the script **fails closed** when the heading is missing or appears twice. Duplicate headings such as "Usage" in two sections of one page would otherwise load the wrong text without any warning.

11. **Ignore headings inside code fences.** A shell comment like `# install deps` inside a fence looks like an H1. A naive parser ends the section there or matches it. The bundled script tracks both ``` and ~~~ fences.

12. **A section ends at the next heading of the same or higher level.** So pulling `## Read-only` includes its `###` children and stops at the next `##`. Structure pages so each heading you reference is a self-contained unit.

13. **Mark the source in the output.** Every rendered section starts with `<!-- path § heading -->`. The agent then knows which file to edit, and nobody edits the rendered text by mistake.

## Budgets

14. **Split instead of raising the cap.** The defaults are 8 KB for the kernel and 16 KB per topic. A topic over budget is covering two tasks, so split it. Allow a per-topic `maxBytes` only for real reference catalogs, and write down why.

15. **Budgets are bytes, not lines.** CJK text is 3 bytes a character, and tokens follow bytes more closely than lines do. Measure with `wc -c`, which is what `check` does.

## Agents and adapters

16. **Keep one instruction file.** Two full copies (AGENTS.md and CLAUDE.md) drift. Keep the rules in AGENTS.md. For an agent without native support, use a one-line pointer file (for Claude Code, a CLAUDE.md with `@AGENTS.md`). Delete the pointer once the agent reads AGENTS.md natively; check its current docs or version rather than assuming.

17. **Skills are adapters, not sources of truth.** A skill that restates the rules forks them. Slim skills to workflow phases that each say "load topic X". Keep the skill's own value, meaning phases, report templates and helper scripts, and nothing more.

18. **Tell the agents that are still running.** Agents that are mid-task in the repo hold the old paths in their context. Before moving files, tell them which topic replaces which section, or they will recreate the old file.

19. **Tell agents where helper files go.** State in the kernel where helper scripts and their state live, such as `scripts/<area>/` and `data/<area>/`. Otherwise agents write them wherever their context last pointed, including old directories outside the repo.

## Staying true

20. **A split without upkeep rots within weeks.** A refactor done once goes stale as soon as the code changes and nobody updates the topic. Self-maintenance needs all four parts:
    - the kernel rule, which makes every task fix stale docs in the same change;
    - the in-repo manual `wiki/ai-context.md`, so no skill is needed;
    - orphan checks;
    - `check` in CI.

    Any part missing and the docs drift back. These checks catch structure, not truth: review changed claims against raw sources and tests. Code is evidence of behavior, not authority to weaken a safety rule or intended requirement.

21. **An orphan is drift you cannot see.** A new wiki page that no topic loads, or a new history file missing from the index, is invisible to agents but looks fine to humans. `check` fails on both, and on a nested `AGENTS.md` that no topic loads. Real exceptions, including scoped instructions agents load by cwd, go under `"unrouted"` with a reason. Keys accept exact paths or case-sensitive fnmatch globs; backslashes normalize to `/`. `projects/*/AGENTS.md` also matches deeper paths because `*` crosses `/`; `**` has no special recursive meaning. Keys match themselves and also act as patterns, regardless of file existence: `wiki/file[1].md` exempts both itself and `wiki/file1.md`. Use `wiki/file[[]1].md` to exempt the literal bracketed filename without also exempting `wiki/file1.md`. Keep patterns narrow: unmatched files must still fail.

22. **Opt in to discover pages outside the wiki.** `"indexed"` must be a list of strings and defaults to `[]`; patterns such as `"projects/*/*-runbook.md"` check `.md` files across repo directories, including hidden, dependency, and build directories but excluding `.git` metadata. Directory symlinks are not followed; patterns and references use real repo-relative paths, and files in real directories are inspected once without alias traversal. Use forward-slash repo-relative patterns: Python `fnmatch` lets `*` cross `/`, is case-sensitive on POSIX, and follows platform normalization on Windows. A matching page must be a topic source (even a heading-selected source), or its full repo-relative path must occur in root instructions, the configured router file, or successfully rendered topic text. A mention below an unselected heading, a basename, or a relative link without that full string does not count. Name it in a topic page, route it, or give an exact path or matching case-sensitive `"unrouted"` glob a nonblank string reason. If multiple exceptions match, any nonblank string reason exempts the page from the indexed check. Blank or non-string reasons still exempt legacy orphans, but do not satisfy an indexed check. Indexed references do not bypass the existing wiki, history, or nested-instructions checks.

23. **Skip bulky trees, not instructions.** `"skipDirs"` stops `check` from walking generated output or evidence dumps that hold thousands of files and no instructions. Never use it to hide a page that should be routed: explicit sources/router remain checked. Each owner's wiki is walked except for mounted trees, which get independent checks.

24. **Mount ownership follows physical trees, not spellings.** Outer automatic orphan/indexed/wiki-link inventories exclude contained mounted roots and file/directory aliases, including modules under the wiki and safe roots with invalid configs. Explicit outer sources/router still get full checks. Each inner root retains its own kernel, references, budgets and exceptions; parent rules cannot rescue it. Preserve lexical link bases even for two sources to one physical file. Mounted display prefixes do not inflate native topic byte caps. Only attach existing strict descendants; no nonempty inner mounts or module-script execution. A missing contained root is a list notice but a check/request failure; invalid config is always an error.
