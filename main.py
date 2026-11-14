import logging
import os
import sys

from dotenv import set_key
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from core.app_paths import app_data_dir, env_file_path, resource_path
from ui.main_window import MainWindow


class ApiKeyDialog(QDialog):
    """First-run setup for the user's Gemini API key."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Set up AI Meeting Assistant")
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self)
        title = QLabel("Connect your Gemini account")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        description = QLabel(
            "Enter your Google AI Studio API key. It will be saved locally "
            "in your macOS Application Support folder and will not be added "
            "to the application bundle."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste Gemini API key")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        link = QLabel('<a href="https://aistudio.google.com/apikey">Get a Gemini API key</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton("Save key", QDialogButtonBox.ButtonRole.AcceptRole)
        self.skip_button = buttons.addButton("Set up later", QDialogButtonBox.ButtonRole.RejectRole)
        self.save_button.clicked.connect(self._save_key)
        self.skip_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _save_key(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API key required", "Paste your Gemini API key, or choose Set up later.")
            return
        try:
            env_path = env_file_path()
            env_path.parent.mkdir(parents=True, exist_ok=True)
            if not env_path.exists():
                env_path.touch(mode=0o600)
            set_key(str(env_path), "GEMINI_API_KEY", key, quote_mode="never")
            os.chmod(env_path, 0o600)
            os.environ["GEMINI_API_KEY"] = key
        except Exception as exc:
            QMessageBox.critical(self, "Could not save API key", str(exc))
            return
        self.accept()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("AI Meeting Assistant")
    app.setOrganizationName("Danish Shirsangi")
    app.setQuitOnLastWindowClosed(True)

    # A normal Dock/Command-Tab entry makes this behave like a regular Mac app.
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyRegular
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except ImportError:
        pass

    icon_path = resource_path("assets/interview-copilot.svg")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    if not os.getenv("GEMINI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv(env_file_path(), override=False)

    if not os.getenv("GEMINI_API_KEY"):
        setup = ApiKeyDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            # Allow opening the app without a key; the user can add one later.
            pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
