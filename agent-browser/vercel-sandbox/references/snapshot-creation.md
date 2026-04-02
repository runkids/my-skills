# Sandbox Snapshot Creation

A **sandbox snapshot** is a saved VM image with system dependencies + agent-browser + Chromium pre-installed. Without one, each run installs deps from scratch (~30s). With one, startup is sub-second.

This is unrelated to agent-browser's *accessibility snapshot* (`agent-browser snapshot`), which dumps a page's accessibility tree.

## Creating a Snapshot

The snapshot reuses the same `CHROMIUM_SYSTEM_DEPS` array from the core pattern:

```ts
import { Sandbox } from "@vercel/sandbox";
import { CHROMIUM_SYSTEM_DEPS, getSandboxCredentials } from "./browser-utils";

async function createSnapshot(): Promise<string> {
  const credentials = getSandboxCredentials();
  const sandbox = await Sandbox.create({
    ...credentials,
    runtime: "node24",
    timeout: 300_000,
  });

  const depsResult = await sandbox.runCommand("sh", [
    "-c",
    `sudo dnf clean all 2>&1 && sudo dnf install -y --skip-broken ${CHROMIUM_SYSTEM_DEPS.join(" ")} 2>&1 && sudo ldconfig 2>&1`,
  ]);
  if ((await depsResult.exitCode()) !== 0) {
    await sandbox.stop();
    throw new Error(`System deps install failed: ${await depsResult.stderr()}`);
  }

  const installResult = await sandbox.runCommand("npm", ["install", "-g", "agent-browser"]);
  if ((await installResult.exitCode()) !== 0) {
    await sandbox.stop();
    throw new Error(`agent-browser install failed: ${await installResult.stderr()}`);
  }

  await sandbox.runCommand("npx", ["agent-browser", "install"]);

  const snapshot = await sandbox.snapshot();
  await sandbox.stop();
  return snapshot.snapshotId;
}
```

Run once, then set the environment variable:

```bash
AGENT_BROWSER_SNAPSHOT_ID=snap_xxxxxxxxxxxx
```

A helper script is available in the demo app:

```bash
npx tsx examples/environments/scripts/create-snapshot.ts
```

Recommended for any production deployment using the Sandbox pattern.
