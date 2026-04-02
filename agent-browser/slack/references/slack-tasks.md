# Slack Task Reference

Step-by-step walkthroughs for common Slack automation tasks. All refs shown below (e.g. `@eNN`) are illustrative — always run `agent-browser snapshot -i` first and use the actual ref for the element you need.

---

## Check All Unread Messages

### Goal
Determine which channels and DMs have unread messages.

### Steps

```bash
# 1. Connect and snapshot
agent-browser connect 9222
agent-browser snapshot -i

# 2. Find and click the Activity tab (look for label "Activity" in snapshot)
agent-browser click @eNN          # ref for Activity tab
agent-browser wait 1000
agent-browser snapshot -i

# 3. Validate: look for unread items or "You've read all the unreads"
agent-browser screenshot activity-unreads.png

# 4. Check DMs tab for unread direct messages
agent-browser snapshot -i          # re-snapshot to find DMs tab ref
agent-browser click @eNN           # ref for DMs tab
agent-browser wait 1000
agent-browser screenshot dms.png

# 5. Check sidebar for "More unreads" button (expands unread channel list)
agent-browser snapshot -i
# If "More unreads" appears, click it to expand
agent-browser click @eNN           # ref for "More unreads"
agent-browser wait 500
agent-browser screenshot expanded-unreads.png
```

### Validation
- Activity tab shows unread items or confirms all-read
- DMs tab shows conversations with unread indicators
- Sidebar unreads list shows channels with new messages

### If something goes wrong
- "More unreads" not visible: you may have no unread channels, or the sidebar needs scrolling — `agent-browser scroll down 300 --selector ".p-sidebar"` then re-snapshot.
- Activity tab shows nothing: wait for load with `agent-browser wait --load networkidle` and re-snapshot.

---

## Navigate to a Channel

### Goal
Open a specific channel by name.

### Steps

```bash
# 1. Snapshot sidebar to find channel
agent-browser snapshot -i

# 2. Look for channel name in treeitem elements (e.g. "engineering")
#    If the channel is not visible, scroll the sidebar
agent-browser scroll down 300 --selector ".p-sidebar"
agent-browser snapshot -i

# 3. Click the channel treeitem ref
agent-browser click @eNN           # ref for the target channel
agent-browser wait --load networkidle

# 4. Validate: confirm channel loaded
agent-browser snapshot -i
agent-browser screenshot channel.png
```

### If something goes wrong
- Channel not in sidebar: use Search instead — snapshot, find the Search button, click it, type the channel name, and select from results.
- Page did not load: `agent-browser wait --load networkidle` and re-snapshot.

---

## Search for Messages

### Goal
Find messages matching specific keywords, optionally filtered by channel, user, or date.

### Steps

```bash
# 1. Snapshot and find Search button
agent-browser snapshot -i
agent-browser click @eNN           # ref for Search button
agent-browser wait 500

# 2. Type search query and submit
agent-browser snapshot -i          # find the search input ref
agent-browser fill @eNN "your search query"
agent-browser press Enter
agent-browser wait --load networkidle

# 3. Capture and review results
agent-browser screenshot search-results.png
agent-browser snapshot -i
```

### Search Filters
Slack supports inline search filters — combine them in the query string:

| Filter | Example |
|--------|---------|
| Channel | `in:engineering` |
| User | `from:@alice` |
| Before date | `before:2026-03-01` |
| After date | `after:2026-02-20` |
| Has file | `has:file` |
| Has reaction | `has:emoji` |

Example: `"bug report" in:engineering from:@alice after:2026-02-20`

### If something goes wrong
- No results: try broader terms or check spelling. Remove filters to verify the keyword matches anything.
- Search input not found after clicking Search: re-snapshot — the input may appear with a short delay.

---

## Extract Channel Information

### Goal
Get a structured list of all visible channels and metadata.

### Steps

```bash
# 1. Get JSON snapshot for programmatic parsing
agent-browser snapshot --json > slack-snapshot.json

# 2. Parse for channel data
# Look for treeitem elements:
#   - level=1 → section headers (Starred, Channels, etc.)
#   - level=2 → individual channels within sections
# Each treeitem's "name" field contains the channel name

# 3. If the channel list is long, scroll and re-snapshot
agent-browser scroll down 500 --selector ".p-sidebar"
agent-browser snapshot --json >> slack-snapshot-page2.json
```

### Validation
- Confirm treeitem elements appear in JSON output
- Cross-check count against what the sidebar shows visually via screenshot

---

## Monitor a Channel for Activity

### Goal
Watch a specific channel and capture recent messages and threads.

### Steps

```bash
# 1. Navigate to the channel (see "Navigate to a Channel" above)
agent-browser click @eNN           # channel ref from snapshot
agent-browser wait --load networkidle

# 2. Capture channel header info (members, topic, description)
agent-browser snapshot -i
agent-browser screenshot channel-header.png

# 3. View recent messages — scroll down to latest
agent-browser scroll down 500
agent-browser screenshot recent-messages.png

# 4. Check threads — look for thread indicator elements in snapshot
agent-browser snapshot -i
# Click a message with thread replies
agent-browser click @eNN           # ref for threaded message
agent-browser wait 500
agent-browser screenshot thread.png
```

### Validation
- Channel header shows expected name, member count, and topic
- Messages are visible and timestamped
- Thread panel opens when clicking a threaded message

---

## Extract User and Message Data

### Goal
Identify who said what, when, and extract structured conversation data.

### Steps

```bash
# 1. Navigate to the target channel or DM
agent-browser click @eNN
agent-browser wait 1000

# 2. Get structured snapshot
agent-browser snapshot --json > conversation.json

# 3. Parse message structure from JSON:
#    - User names: button elements containing the username
#    - Timestamps: link elements with time text (e.g. "Feb 25th at 10:26 AM")
#      The link URL contains Slack's unique message ID (p-prefixed number)
#    - Message content: text content within document/listitem elements
#    - Reactions: button elements showing emoji and count

# 4. Get specific element text
agent-browser get text @eNN        # ref for a specific message element
```

---

## Find Pinned Messages

### Goal
Review messages pinned in a channel.

### Steps

```bash
# 1. Open the channel (see "Navigate to a Channel")
# 2. Snapshot to find the Pins tab (appears near Messages, Files tabs in channel view)
agent-browser snapshot -i
agent-browser click @eNN           # ref for Pins tab
agent-browser wait 500

# 3. Capture pinned messages
agent-browser screenshot pins.png
agent-browser snapshot -i

# 4. Click individual pins to see full context
agent-browser click @eNN           # ref for a specific pin
agent-browser wait 500
agent-browser screenshot pin-detail.png
```

### If something goes wrong
- Pins tab not visible: ensure you are inside a channel view (not the sidebar). Re-navigate to the channel and re-snapshot.

---

## Track Reactions to a Message

### Goal
See who reacted to a message and with what emoji.

### Steps

```bash
# 1. Find the message in channel view
agent-browser snapshot -i
# Look for buttons showing "N reaction(s)" near message elements

# 2. Click the reaction button to expand details
agent-browser click @eNN           # ref for reaction button
agent-browser wait 500

# 3. Capture reaction details (emoji, count, user list)
agent-browser screenshot reactions.png
agent-browser snapshot -i
```

---

## Debugging Checklist

If any task above fails or produces unexpected results:

1. **Screenshot current state**: `agent-browser screenshot debug.png` — compare to what you expected
2. **Check for errors**: `agent-browser errors` — look for page-level issues
3. **Verify URL**: `agent-browser get url` — confirm you are in the right workspace/section
4. **Wait for load**: `agent-browser wait --load networkidle` — Slack's SPA may still be rendering
5. **Scroll**: `agent-browser scroll down 300 --selector ".p-sidebar"` — element may be off-screen
6. **Re-snapshot**: `agent-browser snapshot -i` — always get fresh refs after any state change
