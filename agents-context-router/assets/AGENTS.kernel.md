# AGENTS.md — <project>

<One paragraph: what this repo is and its stack.> This file holds only the rules every task needs. Task details are loaded per topic, so the whole wiki never lands in one context.

## Language

- Instruction files (this file, skills, wiki topic pages), code, identifiers, comments and commits: <English>.
- Reply to the user in <language>.
- Human docs (`README.md`, `wiki/history/`): <language>. Keep new milestone logs in the same language.

## Always Applies

- **<Rule name>.** <A behaviour every task needs, with the one-line trigger for the topic that has the procedure, e.g. "If every run fails the same way, suspect our code first; load `debugging`.">
- **Keep the docs true.** When a doc disagrees with the code, trust the code: verify, then fix the stale doc in the same task. When your change alters behaviour that a topic describes, update that topic page in the same change. Put a new lesson in the kernel as a one-line rule and in its topic as the procedure. Put a finished milestone in `wiki/history/` and add it to the index. Run `python3 scripts/ai-context.py check` after any doc change. The procedure is in the `ai-context` topic.
- **Search before you edit, and change as little as possible.** Match the existing style.
- **Helper files go in the repo.** Put helper scripts in `scripts/<area>/` and their state in `data/<area>/`. Never write them anywhere else.

## Hard Limits

- <Things that must never happen: secrets, destructive commands, outputs outside allowed paths, ports, and so on.>

## Load Context Per Task

```sh
python3 scripts/ai-context.py list      # topics and when to pick them
python3 scripts/ai-context.py <topic>   # print only that topic's sections
python3 scripts/ai-context.py check     # validate paths, headings and byte budgets
```

| Topic | Use when |
|---|---|
| `<topic>` | <one line> |
| `ai-context` | Adding, moving or splitting docs and topics; `check` failures |

Pick the single closest topic. Load a second one only for a task that really crosses two seams.

When no topic fits, read `wiki/README.md`. To add a topic:
1. Put the content in `wiki/`.
2. Map it in `docs/ai-context.json`.
3. List it in both tables.
4. Run `check`.

If a topic goes over budget, split it rather than raising the cap. Skills are workflow adapters that load topics. They are not the source of truth.

## Verification

```sh
<build/test/lint commands>
python3 scripts/ai-context.py check    # doc/topic changes
```
