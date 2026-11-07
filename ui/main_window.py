from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QComboBox, QSplitter
)
from PySide6.QtCore import Qt, QThreadPool
from core.ollama_client import OllamaClient
from core.resume_rag import ResumeRAG
from core.answer_generator import AnswerGenerator
from ui.worker import FunctionWorker
from ui.floating_overlay import FloatingOverlay

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Copilot")
        self.resize(1050, 760)
        self.setMinimumSize(760, 560)
        self.pool = QThreadPool.globalInstance()
        self.ollama = OllamaClient()
        self.rag = ResumeRAG(self.ollama)
        self.generator = AnswerGenerator(self.ollama, self.rag)
        self.history = []
        self.overlay = FloatingOverlay()
        self._build_ui()
        self._check_server()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        top = QHBoxLayout()
        title = QLabel("Interview Copilot")
        title.setStyleSheet("font-size: 23px; font-weight: 700;")
        self.status = QLabel("Checking Ollama…")
        self.status.setStyleSheet("color: #b7791f;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.status)
        root.addLayout(top)

        toolbar = QHBoxLayout()
        self.model = QComboBox()
        self.model.addItems(["qwen3:8b"])
        upload = QPushButton("Upload resume")
        upload.clicked.connect(self.upload_resume)
        show_overlay = QPushButton("Show floating overlay")
        show_overlay.clicked.connect(self.overlay.show)
        clear = QPushButton("Clear conversation")
        clear.clicked.connect(self.clear_chat)
        toolbar.addWidget(QLabel("Chat model:"))
        toolbar.addWidget(self.model)
        toolbar.addWidget(upload)
        toolbar.addWidget(show_overlay)
        toolbar.addWidget(clear)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setPlaceholderText("Your conversation will appear here.")
        self.chat.setStyleSheet("font-size: 14px; padding: 8px;")
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setMaximumHeight(105)
        self.transcript.setPlaceholderText("Resume status and future audio transcript preview.")
        splitter.addWidget(self.chat)
        splitter.addWidget(self.transcript)
        splitter.setSizes([550, 105])
        root.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText("Ask an interview or analytics question…")
        self.question.returnPressed.connect(self.ask)
        self.ask_button = QPushButton("Generate answer")
        self.ask_button.clicked.connect(self.ask)
        bottom.addWidget(self.question, 1)
        bottom.addWidget(self.ask_button)
        root.addLayout(bottom)

        note = QLabel("Local mode · Ollama + ChromaDB · Audio capture will be added in the next milestone")
        note.setStyleSheet("color: #777; font-size: 11px;")
        root.addWidget(note)

    def _check_server(self):
        worker = FunctionWorker(self.ollama.health)
        worker.signals.result.connect(self._server_ok)
        worker.signals.error.connect(lambda e: self.status.setText("Ollama offline — run `ollama serve`"))
        self.pool.start(worker)

    def _server_ok(self, data):
        self.status.setText("Ollama connected")
        self.status.setStyleSheet("color: #16803c;")
        names = [m.get("name") for m in data.get("models", []) if m.get("name")]
        if names:
            self.model.clear()
            self.model.addItems(names)
            if "qwen3:8b" in names:
                self.model.setCurrentText("qwen3:8b")

    def upload_resume(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select resume", str(Path.home()),
            "Documents (*.pdf *.docx *.txt *.md)"
        )
        if not path:
            return
        self.status.setText("Indexing resume…")
        worker = FunctionWorker(self.rag.add_file, path)
        worker.signals.result.connect(lambda count: self._resume_done(path, count))
        worker.signals.error.connect(self._show_error)
        self.pool.start(worker)

    def _resume_done(self, path, count):
        self.status.setText("Resume indexed")
        self.transcript.setPlainText(f"Loaded: {Path(path).name}\nIndexed {count} searchable sections locally.")
        QMessageBox.information(self, "Resume ready", f"Resume indexed successfully.\n{count} sections added to local search.")

    def ask(self):
        question = self.question.text().strip()
        if not question:
            return
        self.ollama.chat_model = self.model.currentText().split(":")[0] + ":" + ":".join(self.model.currentText().split(":")[1:]) if self.model.currentText() else "qwen3:8b"
        self.question.clear()
        self._append("You", question)
        self.ask_button.setEnabled(False)
        self.status.setText("Thinking…")
        worker = FunctionWorker(self.generator.answer, question, list(self.history))
        worker.signals.result.connect(lambda answer: self._answer_done(question, answer))
        worker.signals.error.connect(self._show_error)
        self.pool.start(worker)

    def _answer_done(self, question, answer):
        self._append("Copilot", answer)
        self.history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        self.overlay.set_answer(answer)
        self.ask_button.setEnabled(True)
        self.status.setText("Ready")
        if self.overlay.isVisible():
            self.overlay.raise_()

    def _append(self, speaker, text):
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.chat.append(f"<p><b>{speaker}</b><br>{safe}</p>")

    def _show_error(self, error):
        self.ask_button.setEnabled(True)
        self.status.setText("Error")
        QMessageBox.critical(self, "Interview Copilot error", error)

    def clear_chat(self):
        self.chat.clear()
        self.history.clear()
        self.overlay.set_answer("Your generated answer will appear here.")

    def closeEvent(self, event):
        self.overlay.close()
        event.accept()
