from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt

class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Interview Copilot — Answer")
        self.setMinimumSize(420, 220)
        self.resize(520, 300)
        self.setStyleSheet('''
            QWidget { background: #17191f; color: #f3f4f6; border: 1px solid #414653; }
            QLabel { color: #f3f4f6; font-size: 14px; }
            QPushButton { background: #303642; padding: 7px; border-radius: 5px; }
        ''')
        layout = QVBoxLayout(self)
        self.heading = QLabel("Latest answer")
        self.heading.setStyleSheet("font-weight: 700; font-size: 16px;")
        self.answer = QLabel("Your generated answer will appear here.")
        self.answer.setWordWrap(True)
        self.answer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        close = QPushButton("Hide overlay")
        close.clicked.connect(self.hide)
        layout.addWidget(self.heading)
        layout.addWidget(self.answer, 1)
        layout.addWidget(close)

    def set_answer(self, text):
        self.answer.setText(text)
