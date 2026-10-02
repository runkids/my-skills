# Retry Policy

How workers retry a failed crawl. Read this before changing backoff or pause behaviour.

## Backoff

- Each harbor gets at most three attempts per crawl.
- Wait 1, 4, then 16 minutes between attempts. Add up to 20% random jitter so workers do not retry in lockstep.
- `E_CAPTCHA` is never retried. Pause the harbor immediately.

## Pausing

- After the third failed attempt, set the harbor to `paused` for 6 hours and append the reason to `data/pauses.md`.
- A paused harbor is skipped by the daily batch. Resume it with `make harbor-resume HARBOR=<id>`.

## Limits

- Total retries across all harbors must stay under 40 per hour, or the proxy pool runs dry.
- Never retry a request that already returned rows. `store_rows` is the commit point.
