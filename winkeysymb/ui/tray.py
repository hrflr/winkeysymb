"""System Tray Icon for WinKeySymb."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal


def create_default_icon() -> QIcon:
    """Generate a high-DPI system tray icon programmatically."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded background badge
    painter.setBrush(QColor("#0078d4"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 14, 14)

    # Glyph text
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ω")
    painter.end()

    return QIcon(pixmap)


class WinKeySymbTrayIcon(QSystemTrayIcon):
    open_requested = pyqtSignal()
    hotkey_changed = pyqtSignal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setIcon(create_default_icon())
        self.update_tooltip()
        self._init_menu()
        self.activated.connect(self.on_activated)

    def update_tooltip(self):
        hotkey = self.config.get("hotkey", "Win+Alt+C")
        self.setToolTip(f"WinKeySymb - Special Character Picker ({hotkey})")

    def _init_menu(self):
        menu = QMenu()

        # Open action
        open_action = menu.addAction("Open Character Picker")
        open_action.triggered.connect(lambda: self.open_requested.emit())
        font = open_action.font()
        font.setBold(True)
        open_action.setFont(font)

        menu.addSeparator()

        # Hotkey submenu
        hotkey_menu = menu.addMenu("Global Hotkey")
        options = ["Win+Alt+C", "Win+Alt+Space", "Alt+Shift+Space", "Ctrl+Alt+Space"]
        current_hotkey = self.config.get("hotkey", "Win+Alt+C")

        for opt in options:
            action = hotkey_menu.addAction(opt)
            action.setCheckable(True)
            action.setChecked(opt == current_hotkey)
            action.triggered.connect(lambda checked, h=opt: self.set_hotkey(h))

        # Startup checkbox
        self.startup_action = menu.addAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.config.get("start_on_boot", False))
        self.startup_action.triggered.connect(self.toggle_startup)

        # Copy to clipboard checkbox
        self.clipboard_action = menu.addAction("Always Copy to Clipboard")
        self.clipboard_action.setCheckable(True)
        self.clipboard_action.setChecked(self.config.get("copy_to_clipboard", True))
        self.clipboard_action.triggered.connect(self.toggle_clipboard)

        menu.addSeparator()

        # About
        about_action = menu.addAction("About WinKeySymb")
        about_action.triggered.connect(self.show_about)

        # Exit
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)

        self.setContextMenu(menu)

    def set_hotkey(self, hotkey: str):
        self.config.set("hotkey", hotkey)
        self.update_tooltip()
        self.hotkey_changed.emit(hotkey)
        self._init_menu()

    def toggle_startup(self):
        is_enabled = self.config.toggle_start_on_boot()
        self.startup_action.setChecked(is_enabled)

    def toggle_clipboard(self):
        new_val = not self.config.get("copy_to_clipboard", True)
        self.config.set("copy_to_clipboard", new_val)
        self.clipboard_action.setChecked(new_val)

    def show_about(self):
        hotkey = self.config.get("hotkey", "Win+Alt+C")
        QMessageBox.information(
            None,
            "About WinKeySymb",
            f"WinKeySymb - Special Character Picker\n\n"
            f"Press {hotkey} anywhere to open the picker.\n"
            f"Search math, greek, arrows, typography, and symbols.\n"
            f"Press Enter or click to insert instantly.",
        )

    def exit_app(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def on_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_requested.emit()
