import logging
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
from ui.main_window import MainWindow

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("AI Meeting Assistant")
    # Run as a macOS accessory app: no Dock icon or normal Cmd-Tab entry.
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyAccessory
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except ImportError:
        pass
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "interview-copilot.svg")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
