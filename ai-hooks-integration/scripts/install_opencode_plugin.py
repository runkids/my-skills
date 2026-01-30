#!/usr/bin/env python3
"""Install an OpenCode plugin into the plugins directory.

Usage:
  install_opencode_plugin.py --name my-plugin --output ~/.config/opencode/plugins
  install_opencode_plugin.py --name my-plugin --output ~/.config/opencode/plugins --force
  install_opencode_plugin.py --name my-plugin --output ~/.config/opencode/plugins --websocket
  install_opencode_plugin.py --name my-plugin --output ~/.config/opencode/plugins --advanced

Notes:
  - Creates a plugin that exports a function (required by OpenCode)
  - Uses correct hook parameter names (sessionID, callID, tool)
  - Optional WebSocket event support for external integrations
  - Advanced mode: WebSocket + HTTP fallback, session management, idle detection
"""

import argparse
from pathlib import Path

# Basic template - just hooks
TEMPLATE_BASIC = '''/**
 * {plugin_name} Plugin for OpenCode
 */

module.exports = async function {export_name}(pluginInput) {{
  const cwd = pluginInput?.directory || process.cwd();

  return {{
    "tool.execute.before": async function (input, output) {{
      // input.tool - Tool name (string)
      // input.sessionID - Session identifier
      // input.callID - Unique call ID
      // output.args - Tool arguments (mutable)

      // Example: Block dangerous commands
      if (input.tool === "bash") {{
        const command = output?.args?.command || "";
        if (command.includes("rm -rf /")) {{
          throw new Error("Dangerous command blocked");
        }}
      }}
    }},

    "tool.execute.after": async function (input, output) {{
      // output.title - Execution title
      // output.output - Tool output
      // output.metadata - Additional data

      console.log(`Tool ${{input.tool}} completed`);
    }},
  }};
}};
'''

# WebSocket template - sends events to external server
TEMPLATE_WEBSOCKET = '''/**
 * {plugin_name} Plugin for OpenCode
 *
 * Sends tool execution events to WebSocket server.
 */

const WEBSOCKET_URL = "ws://127.0.0.1:8765";

async function sendEvent(eventType, payload) {{
  try {{
    const WebSocket = (await import("ws")).default;
    const ws = new WebSocket(WEBSOCKET_URL);

    return new Promise((resolve) => {{
      const timeout = setTimeout(() => {{ ws.close(); resolve(); }}, 1000);

      ws.on("open", () => {{
        ws.send(JSON.stringify({{ type: eventType, payload }}));
        clearTimeout(timeout);
        ws.close();
        resolve();
      }});

      ws.on("error", () => {{ clearTimeout(timeout); resolve(); }});
    }});
  }} catch {{
    // Silent fail if ws module not available
  }}
}}

function normalizeToolName(name) {{
  const map = {{
    shell: "Bash", bash: "Bash",
    read: "Read", read_file: "Read",
    write: "Write", write_file: "Write",
    edit: "Edit", edit_file: "Edit",
    grep: "Grep", search_files: "Grep",
    glob: "Glob", list_files: "Glob",
  }};
  return map[(name || "").toLowerCase()] || name || "Unknown";
}}

module.exports = async function {export_name}(pluginInput) {{
  const cwd = pluginInput?.directory || process.cwd();

  return {{
    "tool.execute.before": async function (input, output) {{
      await sendEvent("PreToolUse", {{
        source: "opencode",
        session_id: input.sessionID,
        cwd: cwd,
        tool_name: normalizeToolName(input.tool),
      }});
    }},

    "tool.execute.after": async function (input, output) {{
      await sendEvent("PostToolUse", {{
        source: "opencode",
        session_id: input.sessionID,
        cwd: cwd,
        tool_name: normalizeToolName(input.tool),
      }});
    }},
  }};
}};
'''

# Advanced template - WebSocket + HTTP fallback, session management, idle detection
TEMPLATE_ADVANCED = '''/**
 * {plugin_name} Plugin for OpenCode (Advanced)
 *
 * Features:
 * - WebSocket + HTTP fallback for reliable event delivery
 * - Session ID generation from cwd hash
 * - Idle timeout detection (triggers SessionEnd)
 * - Other AI tool detection (avoids duplicates)
 */

const WEBSOCKET_URL = "ws://127.0.0.1:8765";
const HTTP_URL = "http://127.0.0.1:8766/event";
const IDLE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
const SOURCE = "opencode";

// State
let ws = null;
let wsConnected = false;
let lastActivity = Date.now();
let idleTimer = null;
let currentSessionId = null;

// Generate session ID from cwd
function generateSessionId(cwd) {{
  let hash = 0;
  for (let i = 0; i < cwd.length; i++) {{
    hash = ((hash << 5) - hash) + cwd.charCodeAt(i);
    hash |= 0;
  }}
  return `opencode-${{Math.abs(hash).toString(16)}}`;
}}

// Check if running inside another AI tool (to avoid duplicates)
function isRunningInOtherAI() {{
  const ppid = process.ppid;
  // This is a simplified check - real implementation would walk process tree
  const env = process.env;
  if (env.CLAUDE_SESSION || env.CURSOR_SESSION || env.GEMINI_SESSION) {{
    return true;
  }}
  return false;
}}

// Normalize tool names
function normalizeToolName(name) {{
  const map = {{
    shell: "Bash", bash: "Bash",
    read: "Read", read_file: "Read",
    write: "Write", write_file: "Write",
    edit: "Edit", edit_file: "Edit",
    grep: "Grep", search_files: "Grep",
    glob: "Glob", list_files: "Glob",
  }};
  return map[(name || "").toLowerCase()] || name || "Unknown";
}}

// Send event via HTTP (fallback)
async function sendHttp(event) {{
  try {{
    const response = await fetch(HTTP_URL, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(1000),
    }});
    return response.ok;
  }} catch {{
    return false;
  }}
}}

// Send event via WebSocket
async function sendWs(event) {{
  return new Promise((resolve) => {{
    if (ws && wsConnected) {{
      try {{
        ws.send(JSON.stringify(event));
        resolve(true);
        return;
      }} catch {{}}
    }}

    // Try to connect
    try {{
      const WebSocket = require("ws");
      ws = new WebSocket(WEBSOCKET_URL);

      const timeout = setTimeout(() => {{
        ws.close();
        resolve(false);
      }}, 1000);

      ws.on("open", () => {{
        wsConnected = true;
        clearTimeout(timeout);
        ws.send(JSON.stringify(event));
        resolve(true);
      }});

      ws.on("close", () => {{
        wsConnected = false;
        ws = null;
      }});

      ws.on("error", () => {{
        clearTimeout(timeout);
        wsConnected = false;
        ws = null;
        resolve(false);
      }});
    }} catch {{
      resolve(false);
    }}
  }});
}}

// Send event with fallback
async function sendEvent(eventType, payload) {{
  const event = {{
    event_type: eventType,
    source: SOURCE,
    timestamp: new Date().toISOString(),
    ...payload,
  }};

  // Try WebSocket first, then HTTP
  const wsSent = await sendWs(event);
  if (!wsSent) {{
    await sendHttp(event);
  }}
}}

// Reset idle timer
function resetIdleTimer(sessionId) {{
  lastActivity = Date.now();

  if (idleTimer) {{
    clearTimeout(idleTimer);
  }}

  idleTimer = setTimeout(async () => {{
    await sendEvent("SessionEnd", {{
      session_id: sessionId,
      reason: "idle_timeout",
    }});
    currentSessionId = null;
  }}, IDLE_TIMEOUT_MS);
}}

module.exports = async function {export_name}(pluginInput) {{
  const cwd = pluginInput?.directory || process.cwd();

  // Check for other AI tools
  if (isRunningInOtherAI()) {{
    // Return empty hooks to avoid duplicates
    return {{}};
  }}

  // Generate session ID
  currentSessionId = generateSessionId(cwd);

  // Send SessionStart
  await sendEvent("SessionStart", {{
    session_id: currentSessionId,
    cwd: cwd,
  }});

  resetIdleTimer(currentSessionId);

  return {{
    "tool.execute.before": async function (input, output) {{
      resetIdleTimer(currentSessionId);

      await sendEvent("PreToolUse", {{
        session_id: currentSessionId,
        cwd: cwd,
        tool_name: normalizeToolName(input.tool),
        tool_input: output?.args || {{}},
      }});

      // Example: Block if command accesses other AI configs
      if (input.tool === "bash") {{
        const command = output?.args?.command || "";
        if (command.includes(".claude/") || command.includes(".cursor/")) {{
          throw new Error("Cross-tool config access blocked");
        }}
      }}
    }},

    "tool.execute.after": async function (input, output) {{
      resetIdleTimer(currentSessionId);

      await sendEvent("PostToolUse", {{
        session_id: currentSessionId,
        cwd: cwd,
        tool_name: normalizeToolName(input.tool),
        output: output?.output?.substring?.(0, 500) || "",
      }});
    }},
  }};
}};
'''


def main() -> None:
    ap = argparse.ArgumentParser(description="Install OpenCode plugin")
    ap.add_argument("--name", required=True, help="Plugin file name without extension")
    ap.add_argument("--output", required=True, help="Plugins directory")
    ap.add_argument("--force", action="store_true", help="Overwrite existing file")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    ap.add_argument("--export", dest="export_name", default="PluginHook", help="Exported function name")
    ap.add_argument("--websocket", action="store_true", help="Include WebSocket event sending")
    ap.add_argument(
        "--advanced",
        action="store_true",
        help="Advanced mode: WebSocket + HTTP fallback, session management, idle detection",
    )
    args = ap.parse_args()

    out_dir = Path(args.output).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    plugin_path = out_dir / f"{args.name}.js"
    if plugin_path.exists() and not args.force:
        raise SystemExit(f"File exists: {plugin_path} (use --force to overwrite)")

    if args.advanced:
        template = TEMPLATE_ADVANCED
    elif args.websocket:
        template = TEMPLATE_WEBSOCKET
    else:
        template = TEMPLATE_BASIC
    content = template.format(
        plugin_name=args.name.replace("-", " ").title(),
        export_name=args.export_name,
    )

    if args.dry_run:
        print(f"[dry-run] write {plugin_path}")
        print(content)
        return

    plugin_path.write_text(content)
    print(f"Created: {plugin_path}")


if __name__ == "__main__":
    main()
