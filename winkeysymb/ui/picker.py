"""Win+. style modern floating popup for searching and picking special characters."""

import sys
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt6.QtGui import (
    QFont,
    QColor,
    QKeyEvent,
    QIcon,
    QPainter,
    QBrush,
    QPen,
    QFontMetrics,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QFrame,
    QApplication,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from winkeysymb.data.search import search_symbols
from winkeysymb.memory import trim_memory


class CharacterItemDelegate(QStyledItemDelegate):
    """High-performance delegate to render character cards without creating heavy QWidgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.char_font = QFont("Segoe UI Symbol", 20, QFont.Weight.Bold)
        self.name_font = QFont("Segoe UI", 10, QFont.Weight.Medium)
        self.sub_font = QFont("Segoe UI", 8)
        self.badge_font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        w = option.rect.width() if option.rect.width() > 0 else 400
        return QSize(w, 54)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        try:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            rect = option.rect.adjusted(2, 2, -2, -2)
            from PyQt6.QtWidgets import QStyle
            is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
            is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
            is_top = (index.row() == 0)

            # Card background
            if is_selected:
                painter.setBrush(QColor("#2f3542"))
                painter.setPen(QPen(QColor("#0078d4"), 1.2))
            elif is_hover:
                painter.setBrush(QColor("#2d2d2d"))
                painter.setPen(QPen(QColor("#444444"), 1))
            else:
                painter.setBrush(QColor("#242424"))
                painter.setPen(Qt.PenStyle.NoPen)

            painter.drawRoundedRect(rect, 8, 8)

            # Character glyph box (left)
            box_size = 40
            box_x = rect.x() + 8
            box_y = rect.y() + (rect.height() - box_size) // 2
            box_rect = QRect(box_x, box_y, box_size, box_size)

            painter.setBrush(QColor("#2b2b2b"))
            painter.setPen(QPen(QColor("#3c3c3c"), 1))
            painter.drawRoundedRect(box_rect, 6, 6)

            # Draw character glyph
            painter.setFont(self.char_font)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(box_rect, Qt.AlignmentFlag.AlignCenter, data.get("char", ""))

            # Text layout (middle)
            text_x = box_x + box_size + 12
            name = data.get("name", "")
            latex = data.get("latex", "")
            code_point = data.get("code_point", "")
            category = data.get("category", "")

            # Draw primary name
            painter.setFont(self.name_font)
            painter.setPen(QColor("#f0f0f0"))
            name_rect = QRect(text_x, rect.y() + 8, rect.width() - text_x - 70, 18)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

            # Draw sub-text (tags, latex, codepoint)
            sub_parts = []
            if latex:
                sub_parts.append(latex)
            if code_point:
                sub_parts.append(code_point)
            if category:
                sub_parts.append(category)

            sub_text = "  •  ".join(sub_parts)
            painter.setFont(self.sub_font)
            painter.setPen(QColor("#8e8e93"))
            sub_rect = QRect(text_x, rect.y() + 27, rect.width() - text_x - 70, 16)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub_text)

            # Draw "Enter" badge on top item
            if is_top:
                badge_w = 48
                badge_h = 22
                badge_x = rect.right() - badge_w - 10
                badge_y = rect.y() + (rect.height() - badge_h) // 2
                badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)

                painter.setBrush(QColor("#005fb8"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(badge_rect, 4, 4)

                painter.setFont(self.badge_font)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "↵ Enter")

        except Exception:
            pass
        finally:
            painter.restore()


class CharacterPickerWindow(QWidget):
    """Main floating character search window."""

    character_chosen = pyqtSignal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.target_hwnd: Optional[int] = None
        self.results: List[Dict[str, Any]] = []

        self._setup_window()
        self._init_ui()
        self.refresh_results("")

    def _setup_window(self):
        # Frameless, stays on top, tool window (doesn't steal taskbar space)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(460, 480)

    def _init_ui(self):
        # Outer container layout for drop shadow padding
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Inner container frame with rounded corners and dark theme
        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #383838;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 14, 14, 12)
        container_layout.setSpacing(10)

        # Header with Search bar and Hotkey badge
        search_box = QHBoxLayout()
        search_box.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search special char (e.g. alpha, approx, ->, euro)...")
        self.search_input.setFont(QFont("Segoe UI", 11))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                border-radius: 8px;
                padding: 8px 12px;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
                background-color: #333333;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_box.addWidget(self.search_input, stretch=1)

        hotkey_name = self.config.get("hotkey", "Win+Alt+C")
        self.hotkey_badge = QLabel(hotkey_name)
        self.hotkey_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.hotkey_badge.setStyleSheet("""
            QLabel {
                background-color: #2e2e2e;
                color: #9e9e9e;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 8px;
            }
        """)
        search_box.addWidget(self.hotkey_badge)

        container_layout.addLayout(search_box)

        # Category pills bar
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)
        self.categories = ["All", "Math", "Greek", "Arrows", "Typography", "Currency", "Symbols"]
        self.pill_buttons = []
        for cat in self.categories:
            btn = QPushButton(cat)
            btn.setFont(QFont("Segoe UI", 8))
            btn.setCheckable(True)
            if cat == "All":
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a2a2a;
                    color: #b0b0b0;
                    border: 1px solid #3a3a3a;
                    border-radius: 12px;
                    padding: 3px 10px;
                }
                QPushButton:hover {
                    background-color: #353535;
                    color: #ffffff;
                }
                QPushButton:checked {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: 1px solid #0078d4;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat: self.on_category_clicked(c))
            pills_layout.addWidget(btn)
            self.pill_buttons.append(btn)
        pills_layout.addStretch()
        container_layout.addLayout(pills_layout)

        # Results List View using high-performance Delegate
        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(CharacterItemDelegate(self.list_widget))
        self.list_widget.setFont(QFont("Segoe UI", 10))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        container_layout.addWidget(self.list_widget, stretch=1)

        # Footer hints
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(4, 2, 4, 0)
        
        hint_label = QLabel("↵ Enter: Insert  •  ↑↓: Navigate  •  Esc: Close")
        hint_label.setFont(QFont("Segoe UI", 8))
        hint_label.setStyleSheet("color: #707070;")
        footer_layout.addWidget(hint_label)

        footer_layout.addStretch()
        self.count_label = QLabel("")
        self.count_label.setFont(QFont("Segoe UI", 8))
        self.count_label.setStyleSheet("color: #707070;")
        footer_layout.addWidget(self.count_label)

        container_layout.addLayout(footer_layout)
        outer_layout.addWidget(self.container)

    def on_category_clicked(self, selected_cat: str):
        for btn in self.pill_buttons:
            btn.setChecked(btn.text() == selected_cat)
        if selected_cat == "All":
            self.refresh_results(self.search_input.text())
        else:
            self.refresh_results(self.search_input.text(), category_filter=selected_cat)

    def on_search_changed(self, text: str):
        current_cat = None
        for btn in self.pill_buttons:
            if btn.isChecked() and btn.text() != "All":
                current_cat = btn.text()
                break
        self.refresh_results(text, category_filter=current_cat)

    def refresh_results(self, query: str, category_filter: Optional[str] = None):
        recents = self.config.get_recents()
        all_matches = search_symbols(query, recent_chars=recents)

        if category_filter and category_filter != "All":
            self.results = [m for m in all_matches if m.get("category") == category_filter]
        else:
            self.results = all_matches

        self.list_widget.clear()

        # Populate lightweight list items (delegate handles rendering without child QWidgets)
        for item in self.results:
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            list_item.setSizeHint(QSize(0, 54))
            self.list_widget.addItem(list_item)

        if self.results:
            self.list_widget.setCurrentRow(0)
            self.count_label.setText(f"{len(self.results)} matches")
        else:
            self.count_label.setText("No matches")

    def show_for_target(self, target_hwnd: Optional[int]):
        """Position window properly, remember target window, and open search."""
        self.target_hwnd = target_hwnd
        self.search_input.clear()
        self.refresh_results("")

        # Center in the upper-middle of active screen
        cursor_pos = self.cursor().pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + max(80, (geo.height() - self.height()) // 3)
            self.move(x, y)

        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

    def hide(self):
        super().hide()
        # Trim working set when window hides
        trim_memory()

    def select_and_insert(self, item_index: int):
        if 0 <= item_index < len(self.results):
            chosen_char = self.results[item_index]["char"]
            self.character_chosen.emit(chosen_char)

    def on_item_clicked(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        self.select_and_insert(row)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current_row = self.list_widget.currentRow()
            if current_row < 0 and self.results:
                current_row = 0
            self.select_and_insert(current_row)
            event.accept()
            return
        elif key == Qt.Key.Key_Down:
            current = self.list_widget.currentRow()
            if current < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(current + 1)
            event.accept()
            return
        elif key == Qt.Key.Key_Up:
            current = self.list_widget.currentRow()
            if current > 0:
                self.list_widget.setCurrentRow(current - 1)
            event.accept()
            return

        super().keyPressEvent(event)
