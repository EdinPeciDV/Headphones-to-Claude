# Headphones to Claude

Press the Play/Pause button on your Bluetooth headphones **4 times in a row** and the Claude app (or claude.ai) opens.

Works on Windows. The script registers itself as a silent system media player, so Windows routes the headphone buttons to it instead of Spotify/YouTube — which also means a stray single press won't pause your music while the script is running.

## Setup

### 1. Prerequisites

- Windows 10/11
- Python 3.12 (`py --version`). Install from https://www.python.org/downloads/ if you don't have it.
- Bluetooth headphones already paired with the PC.
- Optional: the Claude desktop app installed at `%LOCALAPPDATA%\AnthropicClaude\claude.exe`. If it isn't there the script falls back to opening https://claude.ai/new in your default browser.

### 2. Clone the repo

```powershell
git clone https://github.com/EdinPeciDV/Headphones-to-Claude.git
cd Headphones-to-Claude
```

### 3. Install the Windows media bindings

```powershell
py -m pip install winrt-runtime winrt-Windows.Foundation winrt-Windows.Media winrt-Windows.Media.Core winrt-Windows.Media.Playback
```

### 4. Run it

```powershell
py claude_headphone_trigger.py
```

You should see:

```
Listening... press the headphone button 4x (any media button counts; up to 2.0s between presses, 6.0s total).
Ctrl+C to stop.
```

Press the Play/Pause button on the headphones 4 times. Each press prints a line like `button: pause  (count=1)`. When the count hits 4, Claude opens.

Stop the script with `Ctrl+C` in the terminal window.

## Tuning

Open `claude_headphone_trigger.py` and change the constants at the top:

```python
TARGET   = 4     # how many presses are needed
WINDOW_S = 6.0   # total seconds the presses must fit inside
GAP_S    = 2.0   # if nothing happens for this long, counter resets
```

Any media button (play, pause, next, previous) counts toward the target — some headphones flip the state after each click, so this makes it robust.

## Run it on startup (optional)

So you don't have to launch it manually every time:

1. Press `Win+R` → type `shell:startup` → Enter. This opens your Startup folder.
2. Right-click → **New** → **Shortcut**.
3. Target:
   ```
   pythonw.exe "C:\full\path\to\Headphones-to-Claude\claude_headphone_trigger.py"
   ```
   (Use `pythonw.exe` instead of `py` so no console window shows up.)
4. Name it "Headphones to Claude" → Finish.

Now the listener starts silently with Windows and the 4-press trigger is always armed.

## Troubleshooting

- **Only `count=1` ever shows and resets** — presses were too far apart; bump `WINDOW_S` and/or `GAP_S`.
- **No `button:` lines at all** — another app has exclusive media-key focus. Close Spotify/YouTube/Groove and restart the script. If you had an AutoHotkey media script running, exit it (tray icon → Exit).
- **ImportError on `winrt.windows.media.playback`** — re-run the `pip install` command above with the exact package names; the dash/dot convention matters.
- **Claude doesn't open** — the script prints `>>> Opening Claude`. If the desktop app path doesn't exist it opens https://claude.ai/new in the browser instead.
