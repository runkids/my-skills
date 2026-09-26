# Gotchas

Each item below is a trap from a real split of an 85 KB README plus AGENTS.md into a 5 KB kernel and 9 topics. Each one says why it matters.

## Content

1. **Keep "every task" and "important" apart.** The kernel test is whether an agent would do something wrong on an unrelated task without this line. Important but task-specific text, like the whole debugging runbook, belongs in a topic. The kernel keeps only the one-line trigger: "if every job fails the same way, suspect our code; load `debugging`". Without the trigger, the agent never loads the topic.

2. **Put lessons in the kernel as behaviour, not as story.** When a user corrects the agent ("it wasn't the site, our code was broken"), turn that into a one-line rule. The incident write-up goes to history.

3. **Move verbatim first, edit second.** Rewriting while moving is how paragraphs vanish. Move whole sections into the history and topic pages in the original language. Then prune duplicates in a separate pass, and compare total bytes against the backup at the end.

4. **Keep history in its original language.** Milestone logs are the evidence trail for humans, so translating them adds risk and helps nobody. Instruction pages that agents read can be English. Human docs can stay in the team's language. State the language rules once, in the kernel.

5. **Leave volatile state out of the docs.** Progress counts, "currently running batch", today's blocker: these belong in a state file or the tracker. A doc that says "7 of 256 done" is wrong by tomorrow and misleads the next agent.

6. **Let a history section be an operating manual when it really is one.** Sometimes a milestone log's "Usage" or "Safety" section is the only precise description of a tool. Do not duplicate it. Reference its exact heading from the topic.

## Routing

7. **Route topics by task, not by file.** "calibration", "debugging" and "export" beat "architecture.md part 2". The agent chooses by what it is about to do. Put a single "use when…" line on each topic.

8. **One topic per task by default.** Say so in the kernel: "pick the single closest topic; load a second only when the task crosses two seams." Otherwise agents load everything "to be safe" and the split buys nothing.

9. **The JSON is the only truth. The tables are mirrors.** `docs/ai-context.json` decides what loads. The tables in `AGENTS.md` and `wiki/README.md` are for discovery. `check` fails when a topic is missing from the kernel table, because an agent cannot choose a topic it has never heard of.

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

    Any part missing and the docs drift back.

21. **An orphan is drift you cannot see.** A new wiki page that no topic loads, or a new history file missing from the index, is invisible to agents but looks fine to humans. `check` fails on both, and on a nested `AGENTS.md` that no topic loads. Real exceptions go under `"unrouted"` with a reason, so each one is a decision rather than an accident.
