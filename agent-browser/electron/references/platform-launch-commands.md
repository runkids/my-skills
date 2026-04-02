# Platform-Specific Launch Commands

Every Electron app supports `--remote-debugging-port` since it is built into Chromium. Use a unique port per app to avoid conflicts.

**Important:** If the app is already running, quit it first and relaunch with the flag. The `--remote-debugging-port` flag must be present at launch time.

## macOS

Pattern: `open -a "AppName" --args --remote-debugging-port=PORT`

```bash
open -a "Slack" --args --remote-debugging-port=9222
open -a "Visual Studio Code" --args --remote-debugging-port=9223
open -a "Discord" --args --remote-debugging-port=9224
open -a "Figma" --args --remote-debugging-port=9225
open -a "Notion" --args --remote-debugging-port=9226
open -a "Spotify" --args --remote-debugging-port=9227
```

## Linux

Pattern: `app-binary --remote-debugging-port=PORT`

```bash
slack --remote-debugging-port=9222
code --remote-debugging-port=9223
discord --remote-debugging-port=9224
```

## Windows

Pattern: `"C:\Users\%USERNAME%\AppData\Local\...\app.exe" --remote-debugging-port=PORT`

```bash
"C:\Users\%USERNAME%\AppData\Local\slack\slack.exe" --remote-debugging-port=9222
"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe" --remote-debugging-port=9223
```
