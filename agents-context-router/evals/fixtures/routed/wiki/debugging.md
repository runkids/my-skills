# Debugging

Work through these in order and stop at the first step that explains the failure.

1. `make worker-status`: every worker needs a heartbeat newer than two minutes.
2. `make proxy-check`: fix our proxy config before touching crawl code.
3. `make screenshot HARBOR=<id>`: a captcha or maintenance page explains most `E_SHAPE` failures.
4. Re-run one harbor with `VERBOSE=1` and read the first stack trace.
5. Only then suspect the site, and pause the harbor.

## Failure codes

| Code | Usual cause | First action |
|---|---|---|
| `E_TIMEOUT` | Slow site or exhausted proxy | `make proxy-check`, then retry once |
| `E_CAPTCHA` | Site started challenging us | Pause the harbor |
| `E_SHAPE` | Table layout changed | Screenshot, then update the parser |
