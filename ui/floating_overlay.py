from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

from ui.macos_window_privacy import set_window_capture_exclusion


class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Meeting Copilot — Answer")
        self.setMinimumSize(420, 220)
        self.resize(520, 300)
        self._capture_privacy_enabled = True
        self.setStyleSheet("""
            QWidget { background: #17191f; color: #f3f4f6; border: 1px solid #414653; }
            QLabel { color: #f3f4f6; font-size: 14px; }
            QPushButton { background: #303642; padding: 7px; border-radius: 5px; }
        """)
        layout = QVBoxLayout(self)
        self.heading = QLabel("Latest answer")
        self.heading.setStyleSheet("font-weight: 700; font-size: 16px;")
        self.answer = QLabel("Your generated response will appear here.")
        self.answer.setWordWrap(True)
        self.answer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        close = QPushButton("Hide overlay")
        close.clicked.connect(self.hide)
        layout.addWidget(self.heading)
        layout.addWidget(self.answer, 1)
        layout.addWidget(close)

    def set_answer(self, text):
        self.answer.setText(text)

    def set_capture_privacy(self, enabled):
        self._capture_privacy_enabled = bool(enabled)
        if self.isVisible():
            return self.apply_capture_privacy()
        return True, "Will apply when the overlay is shown."

    def apply_capture_privacy(self):
        if not self._capture_privacy_enabled:
            return set_window_capture_exclusion(self, False)
        return set_window_capture_exclusion(self, True)

    def showEvent(self, event):
        super().showEvent(event)
        if self._capture_privacy_enabled:
            self.apply_capture_privacy()
