"""Application coordinator for WinKeySymb with lazy UI loading and memory optimization."""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtCore import QObject, pyqtSlot

from winkeysymb.config import ConfigManager
from winkeysymb.hotkey import HotkeyListenerThread
from winkeysymb.injector import get_foreground_window, restore_and_type
from winkeysymb.ui.picker import CharacterPickerWindow
from winkeysymb.ui.tray import WinKeySymbTrayIcon
from winkeysymb.memory import trim_memory


class WinKeySymbApp(QObject):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.tray = WinKeySymbTrayIcon(self.config)
        self.picker = None  # Lazily initialized on first hotkey press

        self.hotkey_thread = None
        self._init_hotkey()

        # Connect signals
        self.tray.open_requested.connect(self.trigger_popup)
        self.tray.hotkey_changed.connect(self.on_hotkey_changed)

        # Show tray icon
        self.tray.show()

        # Trim memory right after launch so idle memory starts ultra-low (~2-5 MB)
        trim_memory()

    def _get_or_create_picker(self) -> CharacterPickerWindow:
        if self.picker is None:
            self.picker = CharacterPickerWindow(self.config)
            self.picker.character_chosen.connect(self.on_character_chosen)
            hotkey_str = self.config.get("hotkey", "Win+Alt+C")
            self.picker.hotkey_badge.setText(hotkey_str)
        return self.picker

    def _init_hotkey(self):
        if self.hotkey_thread:
            self.hotkey_thread.stop()

        hotkey_str = self.config.get("hotkey", "Win+Alt+C")
        self.hotkey_thread = HotkeyListenerThread(hotkey_str)
        self.hotkey_thread.hotkey_triggered.connect(self.trigger_popup)
        self.hotkey_thread.start()

        if self.picker:
            self.picker.hotkey_badge.setText(hotkey_str)

    @pyqtSlot()
    def trigger_popup(self):
        # Capture foreground window right before opening the popup
        target_hwnd = get_foreground_window()
        picker = self._get_or_create_picker()
        picker.show_for_target(target_hwnd)

    @pyqtSlot(str)
    def on_hotkey_changed(self, new_hotkey: str):
        self._init_hotkey()

    @pyqtSlot(str)
    def on_character_chosen(self, char: str):
        picker = self._get_or_create_picker()
        target_hwnd = picker.target_hwnd
        picker.hide()

        # Add to recents
        self.config.add_recent(char)

        # Copy to clipboard if enabled
        if self.config.get("copy_to_clipboard", True):
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(char)

        # Restore window and type character
        restore_and_type(target_hwnd, char)

        # Trim memory back down to idle levels
        trim_memory()

    def cleanup(self):
        if self.hotkey_thread:
            self.hotkey_thread.stop()
        trim_memory()
