# Tidepool Wiki Router

The wiki holds background, procedures, reference tables and history, and no task needs all of it at once. Rules for every task are in the root `AGENTS.md`. The topic-to-section map is in `wiki/ai-context.json`. Load a topic with `python3 scripts/ai-context.py <topic>`.

## Task routing

| Topic | Use when | Main sources |
|---|---|---|
| `build-deploy` | Building, testing or deploying | `build-and-deploy.md` |
| `debugging` | A crawl or worker fails | `debugging.md` |
| `ai-context` | Maintaining this router: add, move or split docs, fix `check` | `ai-context.md` |

`wiki/ai-context.json` is the only source of truth. This table is the human entry point. After changing topics, run `python3 scripts/ai-context.py check`.

## History (milestone logs; read on demand)

| File | Contents |
|---|---|
| `history/m1.md` | 第一版爬蟲：單一港口下載與解析 |
| `history/m2.md` | 多港口與 proxy 池 |
| `history/m3.md` | 校正與匯出 |
| `history/m4.md` | 重試與排程 |
