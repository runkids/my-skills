# AGENTS.md — Tidepool

Tidepool is a crawler that collects tide tables from harbor-authority sites and stores them in Postgres. Stack: Python 3.12, Playwright, Postgres 16. This is the only instruction file for agents. Read all of it before any task.

## Language

- Code, identifiers, comments, commits and this file: English.
- Reply to the user in Traditional Chinese (繁體中文).
- Milestone logs at the bottom are written in Chinese. Keep new logs in Chinese.

## Rules

- Search before you edit, and change as little as possible. Match the existing style.
- Run `make test` before every commit.
- Helper scripts go in `scripts/` and their state in `data/`.
- When a doc disagrees with the code, trust the code and fix the doc in the same change.
- Write commit messages as Conventional Commits.

## Hard limits

- Never commit secrets. `.env` stays local.
- Dev servers use ports 3000-3050 only.
- No deploys on Fridays. No exceptions.
- Write outputs only under `data/` or `out/`.
- Crawl each harbor site at most once per 10 minutes.

## Current status

- Batch run: 7 of 256 harbors done. Batch 8 is running on worker-2.
- Blocker today: the Keelung site returns a captcha.
- Next: finish the remaining 249 harbors, then run the calibration pass.

## Build and test

```sh
make setup          # create venv, install Playwright browsers
make test           # pytest -q, must pass before commit
make lint           # ruff check + ruff format --check
make run-batch N=8  # crawl one batch of harbors
```

## Deploy

1. `make test` and `make lint` are green.
2. Tag the release: `git tag vX.Y.Z`.
3. `make deploy ENV=prod`. The target runs migrations, then restarts workers one at a time.
4. Watch `make logs ENV=prod` for five minutes. Roll back with `make rollback ENV=prod` if error rate rises.

## Tool catalog

| Tool | What it does | Failure codes |
|---|---|---|
| `fetch_table` | Download one harbor's tide table page | `E_TIMEOUT`, `E_CAPTCHA`, `E_HTTP` |
| `parse_table` | Turn the HTML table into rows | `E_SHAPE`, `E_EMPTY` |
| `normalize_units` | Convert feet to meters, local time to UTC | `E_UNIT` |
| `dedupe_rows` | Drop rows already in Postgres | none |
| `store_rows` | Insert rows in one transaction | `E_DB`, `E_CONFLICT` |
| `harbor_list` | List harbors and their crawl state | none |
| `harbor_pause` | Pause one harbor for a number of hours | none |
| `harbor_resume` | Resume a paused harbor | none |
| `proxy_check` | Test the proxy chain end to end | `E_PROXY` |
| `proxy_rotate` | Switch to the next proxy in the pool | `E_PROXY` |
| `captcha_probe` | Detect captcha pages before parsing | none |
| `screenshot` | Save a page screenshot under `out/` | `E_BROWSER` |
| `diff_tables` | Compare two crawls of the same harbor | none |
| `calibrate` | Fit offsets between harbors and reference gauges | `E_FIT` |
| `export_csv` | Write rows to `out/*.csv` | `E_IO` |
| `export_json` | Write rows to `out/*.json` | `E_IO` |
| `backfill` | Re-crawl a date range for one harbor | `E_TIMEOUT`, `E_HTTP` |
| `vacuum_db` | Run VACUUM on the crawl tables | `E_DB` |
| `worker_status` | Show worker heartbeats | none |
| `worker_restart` | Restart one worker | none |

## Debugging runbook

Work through these in order and stop at the first step that explains the failure.

1. Run `make worker-status` and confirm every worker has a heartbeat newer than two minutes. A dead worker looks like a site failure from the outside.
2. Run `make proxy-check`. It tests the proxy chain end to end and prints the first hop that fails. Fix our proxy config before touching crawl code.
3. Run `make screenshot HARBOR=<id>` and open the PNG under `out/`. A captcha, a cookie banner or a maintenance page explains most `E_SHAPE` failures.
4. Re-run one harbor with `make run-batch N=1 HARBOR=<id> VERBOSE=1` and read the first stack trace, not the last one.
5. Compare against the last good crawl with `make diff-tables HARBOR=<id>`. If the layout changed, update the selector in `tidepool/parse.py` and add the saved HTML to `tests/fixtures/`.
6. Only after steps 1 to 5, suspect the site. Pause the harbor with `make harbor-pause HARBOR=<id> HOURS=6` and note the reason in `data/pauses.md`.

Known failure codes:

| Code | Usual cause | First action |
|---|---|---|
| `E_TIMEOUT` | Slow site or exhausted proxy | `make proxy-check`, then retry once |
| `E_CAPTCHA` | Site started challenging us | Pause the harbor; never solve captchas automatically |
| `E_SHAPE` | Table layout changed | Screenshot, then update the parser |
| `E_UNIT` | New unit label in a table header | Add the label to `UNIT_MAP` in `tidepool/units.py` |
| `E_CONFLICT` | Same row inserted by two workers | Check for two workers on one harbor |
| `E_DB` | Connection pool exhausted | `make worker-restart`, then check pool size |

## Database schema

| Table | Key columns | Notes |
|---|---|---|
| `harbors` | `id`, `name`, `site_url`, `state` | `state` is one of `active`, `paused`, `retired` |
| `tide_rows` | `harbor_id`, `ts_utc`, `height_m`, `kind` | `kind` is `high` or `low`; unique on `harbor_id`, `ts_utc`, `kind` |
| `crawls` | `id`, `harbor_id`, `started_at`, `status` | One row per crawl attempt |
| `offsets` | `harbor_id`, `gauge_id`, `offset_cm`, `fitted_at` | Written only by `calibrate` |
| `pauses` | `harbor_id`, `until`, `reason` | Read by `harbor_list` |

Migrations live in `migrations/` and run in filename order. Never edit a migration that has been deployed. Add a new one.

## Release checklist

- Changelog entry added under the next version.
- Migrations tested against a copy of production data.
- `make test` and `make lint` are green on the release commit.
- Workers drained with `make worker-drain` before the migration step.
- On-call notified in the ops channel before and after the deploy.

## Tool details

- `fetch_table` opens the harbor page in Playwright, waits for the `table.tide` selector for up to 20 seconds, and returns the page HTML. It never follows links to other harbors. Set `HEADLESS=0` only on a developer machine.
- `parse_table` expects one header row and one row per tide event. It raises `E_EMPTY` when the table has a header but no rows, which usually means the site shows a maintenance notice.
- `normalize_units` reads the unit from the header cell, not from the row values. Feet become meters with two decimals. Local times use the harbor's own timezone from the `harbors` table.
- `store_rows` writes in one transaction per harbor and per day. A failure rolls back the whole day, so a partial day never reaches the database.
- `proxy_rotate` moves to the next proxy and keeps the old one out of the pool for 30 minutes. Rotating more often than that exhausts the pool.
- `calibrate` needs at least 30 days of rows for a harbor and its reference gauge. With less data it refuses to run instead of fitting a noisy offset.
- `backfill` re-crawls a date range one day at a time and respects the same per-site rate limit as the daily batch.
- `export_csv` and `export_json` write atomically: they write to a temporary file under `out/` and rename it at the end.

## Milestone logs

### M1 — 第一版爬蟲

完成單一港口的潮汐表下載與解析。使用 Playwright 開頁面，等表格載入後取出 HTML，再用 `parse_table` 轉成資料列。驗收：基隆港連續 7 天的資料與官網一致。限制：一次只能處理一個港口，沒有重試。

使用方式：執行 `make run-batch N=1 HARBOR=<id>` 抓取單一港口，結果寫入 `data/` 底下。若表格沒有載入，先用 `make screenshot` 檢查頁面，再調整等待條件。這一版的解析器只認得英文欄位名稱，之後新增的日文與中文港口網站需要另外的對照表。

### M2 — 多港口與 proxy

加入 proxy 池與批次執行，一批 32 個港口。第一次批次執行時所有工作都回傳 ECONNREFUSED，一開始以為是網站當機，換了兩次時間重跑仍然失敗。使用者指正：不是網站的問題，是我們自己的 proxy 設定寫錯了埠號。之後遇到整批工作全部以同一種方式失敗，先檢查我們自己的程式與 proxy，再懷疑網站。驗收：8 批共 256 個港口的清單與狀態表建立完成。

### M3 — 校正與匯出

加入 `calibrate`，用參考潮位站修正各港口的偏移，並完成 `export_csv` 與 `export_json`。注意：絕對不要在共用資料庫執行 `make reset-db`，這會清掉所有港口的歷史資料，而且沒有備份可以還原。要重建資料時，請先在自己的本機資料庫操作。驗收：校正後與參考站的平均誤差小於 5 公分。

### M4 — 重試與排程

加入指數退避重試與每日排程。每個港口最多重試三次，間隔為 1、4、16 分鐘，三次都失敗才標記為 `paused` 並寫入 `data/pauses.md`。排程每天凌晨兩點開始第一批，各批之間間隔二十分鐘，避免同一時間打到同一個網站。驗收：連續七天排程完整執行，沒有任何港口被同一個 worker 重複抓取。已知問題：夏令時間切換當天，凌晨兩點會出現兩次或零次，需要手動檢查當天的批次。
