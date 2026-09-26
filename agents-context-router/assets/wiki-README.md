# <project> Wiki Router

The wiki holds background, procedures, reference tables and history, and no task needs all of it at once. Rules for every task are in the root `AGENTS.md`. The topic-to-section map is in `docs/ai-context.json`. Load a topic with `python3 scripts/ai-context.py <topic>`.

## Task routing

| Topic | Use when | Main sources |
|---|---|---|
| `<topic>` | <one line> | `<page>.md` (the `<heading>` section) |
| `ai-context` | Maintaining this router: add, move or split docs, fix `check` | `ai-context.md` |

`docs/ai-context.json` is the only source of truth. This table is the human entry point. After changing topics, run `python3 scripts/ai-context.py check`.

## History (milestone logs; read on demand)

| File | Contents |
|---|---|
| `history/<milestone>.md` | <one line> |
