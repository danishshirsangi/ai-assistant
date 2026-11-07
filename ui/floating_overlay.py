from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt
from ctypes import c_void_p

try:
    import AppKit
    import objc
except ImportError:
    AppKit = None
    objc = None

class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Interview Copilot — Answer")
        self.setMinimumSize(420, 220)
        self.resize(520, 300)
        self._screen_share_privacy = True
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
        self.privacy_button = QPushButton("Screen-share privacy: ON")
        self.privacy_button.setToolTip("Exclude this overlay from compatible macOS screen-capture APIs.")
        self.privacy_button.clicked.connect(self.toggle_screen_share_privacy)
        close = QPushButton("Hide overlay")
        close.clicked.connect(self.hide)
        layout.addWidget(self.heading)
        layout.addWidget(self.answer, 1)
        layout.addWidget(self.privacy_button)
        layout.addWidget(close)

    def set_answer(self, text):
        self.answer.setText(text)

    def showEvent(self, event):
        super().showEvent(event)
        if self._screen_share_privacy:
            self._apply_screen_share_privacy()

    def toggle_screen_share_privacy(self):
        self._screen_share_privacy = not self._screen_share_privacy
        self.privacy_button.setText(
            "Screen-share privacy: ON" if self._screen_share_privacy
            else "Screen-share privacy: OFF"
        )
        if self._screen_share_privacy and self.isVisible():
            self._apply_screen_share_privacy()
        elif not self._screen_share_privacy:
            self._set_native_sharing(True)

    def _apply_screen_share_privacy(self):
        if AppKit is None or objc is None:
            self.privacy_button.setText("Privacy unavailable (install PyObjC)")
            return
        try:
            native_view = objc.objc_object(c_void_p=int(self.winId()))
            native_window = native_view.window()
            if native_window is None:
                raise RuntimeError("Could not access the native macOS window.")
            native_window.setSharingType_(AppKit.NSWindowSharingNone)
            self.privacy_button.setText("Screen-share privacy: ON")
        except Exception as exc:
            self.privacy_button.setText("Privacy unavailable")
            self.privacy_button.setToolTip(str(exc))

    def _set_native_sharing(self, enabled):
        if AppKit is None or objc is None:
            return
        try:
            native_view = objc.objc_object(c_void_p=int(self.winId()))
            native_window = native_view.window()
            if native_window is not None:
                sharing = (
                    AppKit.NSWindowSharingReadOnly if enabled
                    else AppKit.NSWindowSharingNone
                )
                native_window.setSharingType_(sharing)
        except Exception:
            pass
