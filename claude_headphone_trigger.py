"""
Press the headphone Play/Pause button 4x quickly  -> Claude opens.
Once Claude is the focused window, press any media button once -> start voice
dictation. Recording stops automatically when you pause talking, and the
transcript is typed straight into the Claude window.

Run:   py claude_headphone_trigger.py
Stop:  Ctrl+C in the window
"""
import asyncio
import ctypes
import os
import queue
import threading
import time
import wave
import webbrowser
from ctypes import wintypes
from pathlib import Path

from winrt.windows.foundation import Uri
from winrt.windows.media.core import MediaSource
from winrt.windows.media.playback import MediaCommandEnablingRule, MediaPlayer
from winrt.windows.media.speechrecognition import SpeechRecognizer

TARGET = 4            # presses needed to open Claude when it isn't focused
WINDOW_S = 6.0        # total seconds the 4 presses must fit inside
GAP_S = 2.0           # idle gap after which the press counter resets
CLAUDE_TITLES = ("Claude",)  # substring match against the focused window title

HERE = Path(__file__).resolve().parent
SILENCE = HERE / "silence.wav"
CLAUDE_EXE = Path(os.environ["LOCALAPPDATA"]) / "AnthropicClaude" / "claude.exe"


# --- Win32 glue ---------------------------------------------------------------

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int


def foreground_title() -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def claude_is_focused() -> bool:
    title = foreground_title()
    return any(t in title for t in CLAUDE_TITLES)


# --- Unicode keystroke injection ---------------------------------------------

PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]


class InputI(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", InputI)]


user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(Input), ctypes.c_int]
user32.SendInput.restype = ctypes.c_uint

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


def type_text(text: str) -> None:
    for ch in text:
        for flags in (0, KEYEVENTF_KEYUP):
            inp = Input(
                type=INPUT_KEYBOARD,
                ii=InputI(ki=KeyBdInput(0, ord(ch),
                                        KEYEVENTF_UNICODE | flags, 0, None)),
            )
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(Input))


# --- Speech recognition -------------------------------------------------------

recording = False
recording_lock = threading.Lock()


async def _recognize_once() -> str:
    recognizer = SpeechRecognizer()
    await recognizer.compile_constraints_async()
    result = await recognizer.recognize_async()
    return (result.text or "") if result is not None else ""


def start_voice_capture() -> None:
    global recording
    with recording_lock:
        if recording:
            return
        recording = True
    print(">>> Listening (stop talking to end)")

    def run() -> None:
        global recording
        text = ""
        try:
            text = asyncio.run(_recognize_once())
        except Exception as e:
            print(f"    speech error: {e}")
        finally:
            with recording_lock:
                recording = False

        if not text.strip():
            print("    (nothing heard)")
            return
        print(f"    heard: {text!r}")
        if claude_is_focused():
            type_text(text)
        else:
            print("    (Claude not focused anymore; nothing typed)")

    threading.Thread(target=run, daemon=True).start()


# --- Silence media file -------------------------------------------------------

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


# --- Button plumbing ----------------------------------------------------------

events: "queue.Queue[tuple[str, float]]" = queue.Queue()


def on_press(name: str, args) -> None:
    # Tell the command manager we handled it so Windows keeps sending us the
    # buttons and doesn't flip our silent player's state behind our back.
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
          f"(up to {GAP_S:.1f}s between, {WINDOW_S:.1f}s total) to open Claude.")
    print("With Claude focused, press once to dictate — recording stops when "
          "you stop talking.")
    print("Ctrl+C to stop.")

    presses: list[float] = []
    try:
        while True:
            try:
                name, t = events.get(timeout=0.25)
            except queue.Empty:
                continue

            # Dictation path: Claude is up front, button = push-to-talk.
            if claude_is_focused():
                with recording_lock:
                    busy = recording
                if busy:
                    print(f"button: {name}  (already recording — stay quiet to finish)")
                else:
                    print(f"button: {name}  (Claude focused — dictating)")
                    start_voice_capture()
                presses.clear()
                continue

            # Open-Claude path: 4 presses in the window.
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
