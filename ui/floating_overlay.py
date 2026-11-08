from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from ui.rich_text import format_response_html
from ui.macos_window_privacy import set_window_capture_exclusion


class FloatingOverlay(QWidget):
    """Stable-size translucent overlay; answer content scrolls, never resizes it."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Meeting Copilot — Answer")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._expanded_size = (540, 300)
        self._collapsed = False
        self._capture_privacy_enabled = True
        self.setMinimumSize(420, 220)
        self.resize(*self._expanded_size)

        self.setStyleSheet("""
            QFrame#overlayPanel {
                background-color: rgba(19, 26, 43, 220);
                border: 1px solid rgba(132, 160, 206, 125);
                border-radius: 13px;
            }
            QLabel { color: #f3f6ff; background: transparent; border: none; }
            QLabel#overlayHeading { font-size: 15px; font-weight: 700; color: #b8d5ff; }
            QPushButton {
                color: #eef5ff; background: rgba(65, 93, 143, 190);
                border: 1px solid rgba(132, 160, 206, 115);
                padding: 6px 11px; border-radius: 7px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(85, 120, 182, 220); }
            QTextBrowser {
                background: rgba(12, 19, 33, 175);
                color: #f3f6ff; border: 1px solid rgba(108, 139, 190, 75);
                border-radius: 8px; font-size: 14px; padding: 9px;
                selection-background-color: #4169a5;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.panel = QFrame()
        self.panel.setObjectName("overlayPanel")
        outer.addWidget(self.panel)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.heading = QLabel("✦ Latest answer")
        self.heading.setObjectName("overlayHeading")
        self.collapse_button = QPushButton("−  Collapse")
        self.collapse_button.setToolTip("Collapse the answer into a small button")
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        header_layout.addWidget(self.heading)
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_button)

        self.answer = QTextBrowser()
        self.answer.setReadOnly(True)
        self.answer.setOpenExternalLinks(False)
        self.answer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.answer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()
        hide_button = QPushButton("Hide overlay")
        hide_button.clicked.connect(self.hide)
        footer_layout.addWidget(hide_button)

        layout.addWidget(self.header)
        layout.addWidget(self.answer, 1)
        layout.addWidget(self.footer)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_collapsed(self):
        if not self._collapsed:
            self._expanded_size = (self.width(), self.height())
            self._collapsed = True
            self.answer.hide()
            self.footer.hide()
            self.heading.hide()
            self.collapse_button.setText("▣  Expand answer")
            self.collapse_button.setToolTip("Restore the full answer")
            self.setMinimumSize(0, 0)
            self.setMaximumSize(220, 48)
            self.resize(220, 48)
        else:
            self._collapsed = False
            self.setMaximumSize(16777215, 16777215)
            self.setMinimumSize(420, 220)
            self.heading.show()
            self.answer.show()
            self.footer.show()
            self.collapse_button.setText("−  Collapse")
            self.collapse_button.setToolTip("Collapse the answer into a small button")
            self.resize(*self._expanded_size)

    def set_answer(self, text):
        self.answer.setHtml(format_response_html(text))
        # Keep the beginning of the answer anchored during streaming; the user
        # can scroll down manually whenever they want to read newer content.
        cursor = self.answer.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.answer.setTextCursor(cursor)
        self.answer.verticalScrollBar().setValue(
            self.answer.verticalScrollBar().minimum()
        )
        # Intentionally do not resize: streaming and long answers stay scrollable.

    def set_capture_privacy(self, enabled):
        self._capture_privacy_enabled = bool(enabled)
        if self.isVisible():
            return self.apply_capture_privacy()
        return True, "Will apply when the overlay is shown."

    def apply_capture_privacy(self):
        return set_window_capture_exclusion(self, not self._capture_privacy_enabled)

    def showEvent(self, event):
        super().showEvent(event)
        if self._capture_privacy_enabled:
            self.apply_capture_privacy()
