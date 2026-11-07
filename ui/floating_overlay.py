from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from ui.rich_text import format_response_html
from ui.macos_window_privacy import set_window_capture_exclusion


class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Meeting Copilot — Answer")
        self.setMinimumSize(420, 220)
        self.resize(540, 300)
        self.setMouseTracking(False)
        self._capture_privacy_enabled = True
        self.setStyleSheet("""
            QWidget { background: #17191f; color: #f3f4f6; border: 1px solid #414653; }
            QLabel { color: #f3f4f6; font-size: 14px; }
            QPushButton { background: #303642; padding: 7px; border-radius: 5px; }
            QTextBrowser { background: #17191f; color: #f3f4f6; border: none;
                           font-size: 14px; padding: 4px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.heading = QLabel("Latest answer")
        self.heading.setStyleSheet("font-weight: 700; font-size: 16px;")
        self.answer = QTextBrowser()
        self.answer.setReadOnly(True)
        self.answer.setOpenExternalLinks(False)
        self.answer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.answer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.answer.setMinimumHeight(110)
        self.answer.setStyleSheet("QTextBrowser { border: none; }")
        close = QPushButton("Hide overlay")
        close.clicked.connect(self.hide)
        layout.addWidget(self.heading)
        layout.addWidget(self.answer, 1)
        layout.addWidget(close)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_answer(self, text):
        self.answer.setHtml(format_response_html(text))
        self.answer.document().adjustSize()
        content_height = int(self.answer.document().size().height()) + 34
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        available_height = screen.availableGeometry().height() if screen else 900
        max_height = max(300, int(available_height * 0.72))
        desired_height = min(max_height, max(220, content_height + 92))
        if self.isVisible():
            self.resize(self.width(), desired_height)
        else:
            self.resize(max(self.width(), 540), desired_height)

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
