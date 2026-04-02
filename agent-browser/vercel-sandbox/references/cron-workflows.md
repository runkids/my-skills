# Scheduled Workflows (Cron)

Combine with Vercel Cron Jobs for recurring browser tasks:

```ts
// app/api/cron/route.ts  (or equivalent in your framework)
export async function GET() {
  const result = await withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", "https://example.com/pricing"]);

    const snap = await sandbox.runCommand("agent-browser", ["snapshot", "-i", "-c"]);
    if ((await snap.exitCode()) !== 0) {
      throw new Error(`Snapshot failed: ${await snap.stderr()}`);
    }

    await sandbox.runCommand("agent-browser", ["close"]);
    return await snap.stdout();
  });

  return Response.json({ ok: true, snapshot: result });
}
```

Configure the schedule in `vercel.json`:

```json
{ "crons": [{ "path": "/api/cron", "schedule": "0 9 * * *" }] }
```
