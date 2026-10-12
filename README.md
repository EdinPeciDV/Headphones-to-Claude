# Headphones to Claude

Press the Play/Pause button on your Bluetooth headphones **4 times in a row** and the Claude app (or claude.ai) opens. Then, while Claude is the focused window, **a single press starts voice dictation** — talk, stop talking, and your transcript is typed straight into the chat.

Works on Windows. The script registers itself as a silent system media player, so Windows routes the headphone buttons to it instead of Spotify/YouTube — which also means a stray single press won't pause your music while the script is running.

### Why not "press and hold for 5 seconds"?

Bluetooth headphone media buttons send *discrete* events to Windows (one event per press); the AVRCP protocol doesn't report press duration, so a 5-second hold looks identical to a single tap. The script works around that by checking the focused window instead: when Claude is up front, one press means "dictate".

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

### 3. Install the Windows bindings

```powershell
py -m pip install winrt-runtime winrt-Windows.Foundation winrt-Windows.Media winrt-Windows.Media.Core winrt-Windows.Media.Playback winrt-Windows.Media.SpeechRecognition
```

The last package (`winrt-Windows.Media.SpeechRecognition`) is what lets us use Windows' built-in offline speech recognizer for the voice-to-chat part. On first run Windows may ask to grant microphone access — allow it. If a language pack isn't installed for your Windows display language, the recognizer will say so; install it from **Settings → Time & language → Language → Add a language** with the "Speech" option checked.

### 4. Run it

```powershell
py claude_headphone_trigger.py
```

You should see:

```text
Listening... press the headphone button 4x (up to 2.0s between, 6.0s total) to open Claude.
With Claude focused, press once to dictate — recording stops when you stop talking.
Ctrl+C to stop.
```

**Open Claude:** when Claude isn't the front window, press Play/Pause **4 times**. Each press prints `button: pause  (count=1)` → `(count=2)` …; on the 4th press Claude opens.

**Dictate into Claude:** once Claude is the focused window, press Play/Pause **once**. The script announces `>>> Listening (stop talking to end)`, records from your mic, and the moment you pause the speech recognizer closes the utterance and types the transcript straight into the message box.

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
- **Claude doesn't open** — the script prints `>>> Opening Claude`. If the desktop app path doesn't exist it opens claude.ai/new in the browser instead.
- **Pressing in Claude just prints `(count=1)` instead of starting dictation** — the window-title check didn't match. Confirm your Claude window title contains the word "Claude", or add your actual title substring to `CLAUDE_TITLES` at the top of the script.
- **`speech error: ...` with no transcript** — usually a missing speech language pack. See the install step above, or try saying something longer and clearer; the Windows recognizer times out silence after about 5 seconds.
- **Transcript lands in the wrong window** — it only types when Claude is still the focused window at the moment the recognizer returns. If you Alt-Tab away mid-sentence the script prints `(Claude not focused anymore; nothing typed)` and does not touch any other app.
