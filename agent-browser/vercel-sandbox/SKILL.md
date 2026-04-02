---
name: vercel-sandbox
description: Run agent-browser + Chrome inside Vercel Sandbox microVMs for browser automation from any Vercel-deployed app. Use when the user needs browser automation in a Vercel app (Next.js, SvelteKit, Nuxt, Remix, Astro, etc.), wants to run headless Chrome without binary size limits, needs persistent browser sessions across commands, or wants ephemeral isolated browser environments. Triggers include "Vercel Sandbox browser", "microVM Chrome", "agent-browser in sandbox", "browser automation on Vercel", or any task requiring Chrome in a Vercel Sandbox.
---

# Browser Automation with Vercel Sandbox

Run agent-browser + headless Chrome inside ephemeral Vercel Sandbox microVMs. A Linux VM spins up on demand, executes browser commands, and shuts down. Works with any Vercel-deployed framework.

## Dependencies

```bash
pnpm add @vercel/sandbox
```

Use sandbox snapshots to pre-install Chromium and agent-browser for sub-second startup. See `references/snapshot-creation.md`.

## Core Pattern

```ts
import { Sandbox } from "@vercel/sandbox";

// System libraries required by Chromium on the sandbox VM (Amazon Linux / dnf)
// Defined once — reuse in snapshot creation (see references/snapshot-creation.md)
const CHROMIUM_SYSTEM_DEPS = [
  "nss", "nspr", "libxkbcommon", "atk", "at-spi2-atk", "at-spi2-core",
  "libXcomposite", "libXdamage", "libXrandr", "libXfixes", "libXcursor",
  "libXi", "libXtst", "libXScrnSaver", "libXext", "mesa-libgbm", "libdrm",
  "mesa-libGL", "mesa-libEGL", "cups-libs", "alsa-lib", "pango", "cairo",
  "gtk3", "dbus-libs",
];

function getSandboxCredentials() {
  if (
    process.env.VERCEL_TOKEN &&
    process.env.VERCEL_TEAM_ID &&
    process.env.VERCEL_PROJECT_ID
  ) {
    return {
      token: process.env.VERCEL_TOKEN,
      teamId: process.env.VERCEL_TEAM_ID,
      projectId: process.env.VERCEL_PROJECT_ID,
    };
  }
  return {};
}

async function withBrowser<T>(
  fn: (sandbox: InstanceType<typeof Sandbox>) => Promise<T>,
  timeoutMs = 120_000,
): Promise<T> {
  const snapshotId = process.env.AGENT_BROWSER_SNAPSHOT_ID;
  const credentials = getSandboxCredentials();

  const sandbox = snapshotId
    ? await Sandbox.create({
        ...credentials,
        source: { type: "snapshot", snapshotId },
        timeout: timeoutMs,
      })
    : await Sandbox.create({ ...credentials, runtime: "node24", timeout: timeoutMs });

  if (!snapshotId) {
    const depsResult = await sandbox.runCommand("sh", [
      "-c",
      `sudo dnf clean all 2>&1 && sudo dnf install -y --skip-broken ${CHROMIUM_SYSTEM_DEPS.join(" ")} 2>&1 && sudo ldconfig 2>&1`,
    ]);
    if ((await depsResult.exitCode()) !== 0) {
      await sandbox.stop();
      throw new Error(`Chromium deps install failed: ${await depsResult.stderr()}`);
    }

    const installResult = await sandbox.runCommand("npm", ["install", "-g", "agent-browser"]);
    if ((await installResult.exitCode()) !== 0) {
      await sandbox.stop();
      throw new Error(`agent-browser install failed: ${await installResult.stderr()}`);
    }

    await sandbox.runCommand("npx", ["agent-browser", "install"]);
  }

  try {
    return await fn(sandbox);
  } finally {
    await sandbox.stop();
  }
}
```

## Screenshot

```ts
export async function screenshotUrl(url: string) {
  return withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", url]);

    const titleResult = await sandbox.runCommand("agent-browser", [
      "get", "title", "--json",
    ]);
    const title = JSON.parse(await titleResult.stdout())?.data?.title || url;

    const ssResult = await sandbox.runCommand("agent-browser", [
      "screenshot", "--json",
    ]);
    const ssData = JSON.parse(await ssResult.stdout());
    if (!ssData?.data?.path) {
      throw new Error("Screenshot failed — no file path returned");
    }
    const b64Result = await sandbox.runCommand("base64", ["-w", "0", ssData.data.path]);
    const screenshot = (await b64Result.stdout()).trim();

    await sandbox.runCommand("agent-browser", ["close"]);
    return { title, screenshot };
  });
}
```

## Accessibility Snapshot

```ts
export async function snapshotUrl(url: string) {
  return withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", url]);

    const titleResult = await sandbox.runCommand("agent-browser", [
      "get", "title", "--json",
    ]);
    const title = JSON.parse(await titleResult.stdout())?.data?.title || url;

    const snapResult = await sandbox.runCommand("agent-browser", [
      "snapshot", "-i", "-c",
    ]);
    if ((await snapResult.exitCode()) !== 0) {
      throw new Error(`Snapshot failed: ${await snapResult.stderr()}`);
    }
    const snapshot = await snapResult.stdout();

    await sandbox.runCommand("agent-browser", ["close"]);
    return { title, snapshot };
  });
}
```

## Multi-Step Workflows

The sandbox persists between commands, so you can run full automation sequences. The accessibility snapshot returns lines like `@e3 textbox "Email"` — use the `@eN` references to target elements:

```ts
export async function fillAndSubmitForm(url: string, data: Record<string, string>) {
  return withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", url]);

    // Get accessibility snapshot with interactive elements
    const snapResult = await sandbox.runCommand("agent-browser", [
      "snapshot", "-i",
    ]);
    const snapshot = await snapResult.stdout();

    // Each interactive line looks like: @e3 textbox "Email"
    // Build a map of label → element ref for targeted filling
    const refMap = new Map<string, string>();
    for (const line of snapshot.split("\n")) {
      const match = line.match(/^(@e\d+)\s+\w+\s+"(.+)"/);
      if (match) refMap.set(match[2].toLowerCase(), match[1]);
    }

    for (const [label, value] of Object.entries(data)) {
      const ref = refMap.get(label.toLowerCase());
      if (!ref) throw new Error(`No element found for label "${label}"`);
      await sandbox.runCommand("agent-browser", ["fill", ref, value]);
    }

    // Click submit — find the button ref from the snapshot
    const submitRef = refMap.get("submit") ?? "@e5";
    await sandbox.runCommand("agent-browser", ["click", submitRef]);
    await sandbox.runCommand("agent-browser", ["wait", "--load", "networkidle"]);

    const ssResult = await sandbox.runCommand("agent-browser", [
      "screenshot", "--json",
    ]);
    const ssData = JSON.parse(await ssResult.stdout());
    if (!ssData?.data?.path) {
      throw new Error("Screenshot failed — no file path returned");
    }
    const b64Result = await sandbox.runCommand("base64", ["-w", "0", ssData.data.path]);
    const screenshot = (await b64Result.stdout()).trim();

    await sandbox.runCommand("agent-browser", ["close"]);
    return { screenshot };
  });
}
```

## Authentication

On Vercel deployments, the Sandbox SDK authenticates automatically via OIDC. For local development, set:

```bash
VERCEL_TOKEN=<personal-access-token>
VERCEL_TEAM_ID=<team-id>
VERCEL_PROJECT_ID=<project-id>
```

When absent, the SDK falls back to `VERCEL_OIDC_TOKEN` (automatic on Vercel).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AGENT_BROWSER_SNAPSHOT_ID` | No (recommended) | Pre-built snapshot ID for sub-second startup. See `references/snapshot-creation.md` |
| `VERCEL_TOKEN` | No | Personal access token (local dev only; OIDC is automatic on Vercel) |
| `VERCEL_TEAM_ID` | No | Team ID (local dev only) |
| `VERCEL_PROJECT_ID` | No | Project ID (local dev only) |

## Further Reading

- `references/snapshot-creation.md` — Creating and managing sandbox snapshots
- `references/cron-workflows.md` — Scheduled browser tasks with Vercel Cron Jobs
- `examples/environments/` in the agent-browser repo — Working app with streaming UI and rate limiting
