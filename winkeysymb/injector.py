"""Injects characters into previously active Windows applications."""

import time
import ctypes
from ctypes import wintypes
from typing import Optional

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def get_foreground_window() -> int:
    """Return the handle of the currently active window."""
    return user32.GetForegroundWindow()


def restore_and_type(target_hwnd: Optional[int], text: str):
    """Restore target window and type the text via SendInput."""
    if target_hwnd and target_hwnd != 0:
        # Give focus back to the target window
        user32.SetForegroundWindow(target_hwnd)
        # Small wait for Windows to switch focus
        time.sleep(0.04)

    # Send Unicode key events
    for char in text:
        encoded = char.encode("utf-16-le")
        for i in range(0, len(encoded), 2):
            code_unit = int.from_bytes(encoded[i : i + 2], "little")

            # Key Down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.u.ki = KEYBDINPUT(
                wVk=0,
                wScan=code_unit,
                dwFlags=KEYEVENTF_UNICODE,
                time=0,
                dwExtraInfo=None,
            )

            # Key Up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.u.ki = KEYBDINPUT(
                wVk=0,
                wScan=code_unit,
                dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=None,
            )

            inputs = (INPUT * 2)(inp_down, inp_up)
            user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
