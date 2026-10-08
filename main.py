"""Main entry point for WinKeySymb."""

import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure package root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# PyInstaller --windowed redirects stdout/stderr to None, causing prints to crash.
# Redirect them safely to a log file.
try:
    log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "winkeysymb")
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(os.path.join(log_dir, "winkeysymb.log"), "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file
except Exception:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

from winkeysymb.app import WinKeySymbApp


_MUTEX_HANDLE = None

def ensure_single_instance() -> bool:
    """Ensure only one instance of WinKeySymb runs at a time."""
    global _MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    mutex_name = "Local\\WinKeySymbSpecialCharPickerSingleInstanceMutex"
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return False
    return True


def main():
    # Windows high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("WinKeySymb")
    app.setApplicationDisplayName("WinKeySymb Character Picker")

    # Don't quit when picker window closes - stay alive in system tray!
    app.setQuitOnLastWindowClosed(False)

    if not ensure_single_instance():
        print("[WinKeySymb] Another instance is already running.")
        sys.exit(0)

    winkeysymb_app = WinKeySymbApp()

    # Show initial notification / tray balloon on first start
    if winkeysymb_app.tray.isSystemTrayAvailable():
        hotkey = winkeysymb_app.config.get("hotkey", "Win+Alt+C")
        winkeysymb_app.tray.showMessage(
            "WinKeySymb Active",
            f"Press {hotkey} anywhere to open the special character picker.",
            winkeysymb_app.tray.icon(),
            3000,
        )

    from winkeysymb.memory import trim_memory
    trim_memory()

    ret = app.exec()
    winkeysymb_app.cleanup()
    sys.exit(ret)


if __name__ == "__main__":
    main()
