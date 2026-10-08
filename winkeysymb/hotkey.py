"""Global hotkey listener using Win32 RegisterHotKey in a background QThread."""

import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QThread, pyqtSignal

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

HOTKEY_ID = 10101

# Virtual Key Codes mapping
VK_MAP = {
    "SPACE": 0x20,
    "RETURN": 0x0D,
    "ENTER": 0x0D,
    "PERIOD": 0xBE,
    ".": 0xBE,
    "/": 0xBF,
    ";": 0xBA,
}
# A-Z
for ch in range(ord('A'), ord('Z') + 1):
    VK_MAP[chr(ch)] = ch
# 0-9
for ch in range(ord('0'), ord('9') + 1):
    VK_MAP[chr(ch)] = ch


def parse_hotkey_string(hotkey_str: str):
    """Parse string like 'Win+Alt+C' into (mods, vk)."""
    parts = [p.strip().upper() for p in hotkey_str.split("+")]
    mods = MOD_NOREPEAT
    vk = None

    for part in parts:
        if part in ("WIN", "WINDOWS", "SUPER"):
            mods |= MOD_WIN
        elif part in ("ALT", "MENU"):
            mods |= MOD_ALT
        elif part in ("CTRL", "CONTROL"):
            mods |= MOD_CONTROL
        elif part in ("SHIFT",):
            mods |= MOD_SHIFT
        else:
            vk = VK_MAP.get(part, None)
            if vk is None and len(part) == 1:
                vk = ord(part)

    if vk is None:
        vk = ord('C')
    return mods, vk


class HotkeyListenerThread(QThread):
    hotkey_triggered = pyqtSignal()
    registration_failed = pyqtSignal(str)

    def __init__(self, hotkey_str: str = "Win+Alt+C"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self._thread_id = 0
        self._is_running = True

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        mods, vk = parse_hotkey_string(self.hotkey_str)

        # Register hotkey on this thread's message queue
        success = user32.RegisterHotKey(0, HOTKEY_ID, mods, vk)
        if not success:
            err_msg = f"Could not register hotkey {self.hotkey_str}. It might be used by another app."
            print(f"[WinKeySymb] {err_msg}")
            self.registration_failed.emit(err_msg)
            # Try fallback to Alt+Shift+Space
            fallback_mods = MOD_ALT | MOD_SHIFT | MOD_NOREPEAT
            fallback_vk = 0x20
            if user32.RegisterHotKey(0, HOTKEY_ID, fallback_mods, fallback_vk):
                print("[WinKeySymb] Registered fallback hotkey: Alt+Shift+Space")
            else:
                return

        print(f"[WinKeySymb] Hotkey active: {self.hotkey_str}")

        msg = wintypes.MSG()
        while self._is_running:
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:  # WM_QUIT or error
                break
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.hotkey_triggered.emit()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnregisterHotKey(0, HOTKEY_ID)

    def stop(self):
        self._is_running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self.wait(1000)
