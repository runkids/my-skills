# AGENTS.md — Tidepool

Tidepool crawls harbor tide tables into Postgres (Python 3.12, Playwright, Postgres 16). This file holds only the rules every task needs. Task details are loaded per topic, so the whole wiki never lands in one context.

## Language

- Instruction files, code, identifiers, comments and commits: English.
- Reply to the user in Traditional Chinese (繁體中文).
- Human docs (`README.md`, `wiki/history/`): Chinese. Keep new milestone logs in Chinese.

## Always Applies

- **Keep the docs true.** Verify descriptive claims against code and tests, then fix stale docs. A conflict with a hard limit, safety rule or intended requirement is not permission to weaken that rule: surface the conflict and resolve it with the owner. When your change alters behaviour that a topic describes, update that topic page in the same change. Put a finished milestone in `wiki/history/` and add it to the index. Run `python3 scripts/ai-context.py check` after any doc change. The procedure is in the `ai-context` topic.
- **Search before you edit, and change as little as possible.** Match the existing style.
- **Helper files go in the repo.** Put helper scripts in `scripts/` and their state in `data/`.

## Hard Limits

- Never commit secrets. `.env` stays local.
- Never run `make reset-db` on the shared database.
- Dev servers use ports 3000-3050 only. No deploys on Fridays.

## Load Context Per Task

```sh
python3 scripts/ai-context.py list      # topics and when to pick them
python3 scripts/ai-context.py <topic>   # print only that topic's sections
python3 scripts/ai-context.py check     # validate paths, headings and byte budgets
```

| Topic | Use when |
|---|---|
| `build-deploy` | Building, testing or deploying |
| `debugging` | A crawl or worker fails |
| `ai-context` | Adding, moving or splitting docs and topics; `check` failures |

Pick the single closest topic. Load a second one only for a task that really crosses two seams.

This table lists local topics; use `list` for mounted topics such as `kb/guide`, whose config, instructions and index belong to their own root.

When no topic fits, read `wiki/README.md`. If routed context is incomplete or contradictory, inspect the relevant raw source, code or tests before acting; do not load the whole wiki by default. To add a topic:
1. Put the content in `wiki/`.
2. Map it in `wiki/ai-context.json`.
3. List it in this root's two local tables.
4. Run `check`.

## Verification

```sh
make test
python3 scripts/ai-context.py check    # doc/topic changes
```
