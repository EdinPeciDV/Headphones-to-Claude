"""
Press the headphone Play/Pause button 4x quickly -> Claude opens.

Bluetooth headphone buttons on Windows go through the system media controls,
not the keyboard, so this script registers itself as a (silent) media player.
While it's running, it receives the headphone button presses.

Run:   py claude_headphone_trigger.py
Stop:  Ctrl+C in the window
"""
import os
import queue
import time
import wave
import webbrowser
from pathlib import Path

from winrt.windows.foundation import Uri
from winrt.windows.media.core import MediaSource
from winrt.windows.media.playback import MediaCommandEnablingRule, MediaPlayer

TARGET = 4        # presses needed
WINDOW_S = 6.0    # total seconds the 4 presses must fit inside
GAP_S = 2.0       # if nothing happens for this long, counter resets

HERE = Path(__file__).resolve().parent
SILENCE = HERE / "silence.wav"
CLAUDE_EXE = Path(os.environ["LOCALAPPDATA"]) / "AnthropicClaude" / "claude.exe"


def make_silence(path: Path, seconds: int = 5, rate: int = 8000) -> None:
    if path.exists():
        return
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * seconds)


def open_claude() -> None:
    print(">>> Opening Claude")
    if CLAUDE_EXE.exists():
        os.startfile(CLAUDE_EXE)
    else:
        webbrowser.open("https://claude.ai/new")


events: "queue.Queue[tuple[str, float]]" = queue.Queue()


def on_press(name: str, args) -> None:
    # Tell the command manager "we handled it" so Windows doesn't change our
    # player's state behind our back and keeps sending us the buttons.
    args.handled = True
    events.put((name, time.monotonic()))


def main() -> None:
    make_silence(SILENCE)

    player = MediaPlayer()
    cm = player.command_manager
    cm.is_enabled = True
    for behavior in (cm.play_behavior, cm.pause_behavior,
                     cm.next_behavior, cm.previous_behavior):
        behavior.enabling_rule = MediaCommandEnablingRule.ALWAYS

    cm.add_play_received(lambda s, a: on_press("play", a))
    cm.add_pause_received(lambda s, a: on_press("pause", a))
    cm.add_next_received(lambda s, a: on_press("next", a))
    cm.add_previous_received(lambda s, a: on_press("previous", a))

    player.source = MediaSource.create_from_uri(Uri(SILENCE.as_uri()))
    player.is_looping_enabled = True
    player.play()

    print(f"Listening... press the headphone button {TARGET}x "
          f"(any media button counts; up to {GAP_S:.1f}s between presses, "
          f"{WINDOW_S:.1f}s total).")
    print("Ctrl+C to stop.")

    presses: list[float] = []
    try:
        while True:
            try:
                name, t = events.get(timeout=0.25)
            except queue.Empty:
                continue
            # Drop presses that are either too old overall or came after a long
            # idle gap — so a stray press hours ago doesn't count.
            if presses and (t - presses[-1] > GAP_S):
                presses.clear()
            presses = [p for p in presses if t - p <= WINDOW_S]
            presses.append(t)
            print(f"button: {name}  (count={len(presses)})")
            if len(presses) >= TARGET:
                presses.clear()
                open_claude()
    except KeyboardInterrupt:
        player.pause()


if __name__ == "__main__":
    main()
