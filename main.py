import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Interview Copilot")
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "interview-copilot.svg")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
