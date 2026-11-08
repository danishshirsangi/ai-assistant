from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QComboBox, QSplitter
)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QIcon, QTextCursor
from core.ollama_client import OllamaClient
from core.resume_rag import ResumeRAG
from core.answer_generator import AnswerGenerator
from ui.worker import FunctionWorker
from ui.rich_text import format_response_html
from ui.macos_window_privacy import set_window_capture_exclusion


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Copilot")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "assets" / "interview-copilot.svg")))
        # Keep the single main application window above other app windows.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1050, 760)
        self.setMinimumSize(760, 560)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #e8eef8; }
            QLabel { color: #e8eef8; }
            QLineEdit, QTextEdit, QComboBox {
                background: #1b2638; color: #edf4ff;
                border: 1px solid #344763; border-radius: 7px;
                padding: 7px; selection-background-color: #4169a5;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #79a9ed;
            }
            QPushButton {
                background: #263a58; color: #f2f6ff;
                border: 1px solid #405c83; border-radius: 7px;
                padding: 7px 12px; font-weight: 600;
            }
            QPushButton:hover { background: #34527b; }
            QPushButton:pressed { background: #1d2d45; }
            QPushButton:disabled { color: #7f8da3; background: #202b3b; }
            QComboBox QAbstractItemView {
                background: #1b2638; color: #edf4ff;
                selection-background-color: #34527b;
            }
            QSplitter::handle { background: #293a52; }
        """)
        self.pool = QThreadPool.globalInstance()
        self.ollama = OllamaClient()
        self.rag = ResumeRAG(self.ollama)
        self.generator = AnswerGenerator(self.ollama, self.rag)
        self.history = []
        self._streamed_answer = ""
        self._capture_privacy_enabled = True
        self.audio = None
        self._build_ui()
        self._setup_audio()
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
        clear = QPushButton("Clear conversation")
        clear.clicked.connect(self.clear_chat)
        self.privacy_button = QPushButton("Capture privacy: ON")
        self.privacy_button.setToolTip(
            "Request exclusion of the main Interview Copilot window from compatible macOS capture APIs. "
            "This is best-effort and not a universal screen-sharing guarantee."
        )
        self.privacy_button.clicked.connect(self._toggle_capture_privacy)
        toolbar.addWidget(QLabel("Chat model:"))
        toolbar.addWidget(self.model)
        toolbar.addWidget(upload)
        toolbar.addWidget(clear)
        toolbar.addWidget(self.privacy_button)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setPlaceholderText("Your conversation will appear here.")
        self.chat.setStyleSheet("font-size: 14px; padding: 8px;")
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setMaximumHeight(125)
        self.transcript.setPlaceholderText("Transcript appears here after you stop recording.")
        self.answer_view = QTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setPlaceholderText(
            "The latest answer will appear here and stream live while the model generates it."
        )
        self.answer_view.setStyleSheet("font-size: 15px; padding: 10px;")
        self.answer_view.setMinimumHeight(150)

        splitter.addWidget(self.chat)
        splitter.addWidget(self.answer_view)
        splitter.addWidget(self.transcript)
        splitter.setSizes([330, 300, 110])
        root.addWidget(splitter, 1)

        audio_bar = QHBoxLayout()
        self.record_button = QPushButton("Start recording")
        self.record_button.setToolTip("Press Control + Option + R once to start recording; press again to stop. You can also use this button.")
        self.record_button.clicked.connect(self._toggle_recording)
        self.microphone = QComboBox()
        self.microphone.setMinimumWidth(210)
        self.microphone.setToolTip("Choose the microphone used for your voice.")
        self.microphone.addItem("System default (macOS)", None)
        self.refresh_microphones_button = QPushButton("Refresh")
        self.refresh_microphones_button.setToolTip("Refresh available microphones.")
        self.refresh_microphones_button.clicked.connect(self._refresh_microphones)
        self.audio_hint = QLabel("Mic + system audio · local transcription")
        self.audio_hint.setStyleSheet("color: #777; font-size: 11px;")
        audio_bar.addWidget(self.record_button)
        audio_bar.addWidget(QLabel("Microphone:"))
        audio_bar.addWidget(self.microphone)
        audio_bar.addWidget(self.refresh_microphones_button)
        audio_bar.addWidget(self.audio_hint, 1)
        root.addLayout(audio_bar)

        bottom = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText("Ask an interview or analytics question…")
        self.question.returnPressed.connect(self.ask)
        self.ask_button = QPushButton("Generate answer")
        self.ask_button.clicked.connect(self.ask)
        bottom.addWidget(self.question, 1)
        bottom.addWidget(self.ask_button)
        root.addLayout(bottom)

        note = QLabel("Local mode · Ollama + SQLite · audio captured and transcribed on this Mac")
        note.setStyleSheet("color: #777; font-size: 11px;")
        root.addWidget(note)

    def showEvent(self, event):
        super().showEvent(event)
        if self._capture_privacy_enabled:
            self._apply_capture_privacy()

    def _toggle_capture_privacy(self):
        self._capture_privacy_enabled = not self._capture_privacy_enabled
        self._apply_capture_privacy()

    def _apply_capture_privacy(self):
        enabled = self._capture_privacy_enabled
        self.privacy_button.setText(
            "Capture privacy: ON" if enabled else "Capture privacy: OFF"
        )
        ok, detail = set_window_capture_exclusion(self, enabled)
        if not ok:
            self.privacy_button.setText(
                "Capture privacy: ON (unavailable)" if enabled else "Capture privacy: OFF"
            )
            self.privacy_button.setToolTip(
                "Could not apply privacy to the main window: " + detail +
                "\\nMeeting-app behaviour varies; this is not a universal guarantee."
            )
        else:
            self.privacy_button.setToolTip(
                "The main window is set to " +
                ("exclude from" if enabled else "allow") +
                " compatible macOS capture APIs. Meeting-app behaviour varies."
            )

    def _setup_audio(self):
        try:
            from audio.controller import AudioController
            self.audio = AudioController()
            self.audio.recording_changed.connect(self._recording_changed)
            self.audio.transcript_ready.connect(self._audio_transcript_ready)
            self.audio.error.connect(self._audio_error)
            self.microphone.currentIndexChanged.connect(self._microphone_changed)
            self._refresh_microphones()
            self.audio.start_hotkey_listener()
            self.audio_hint.setText("⌃⌥R to start · press again to stop · local audio only")
        except Exception as exc:
            self.audio_hint.setText("Audio dependencies unavailable. Install requirements-audio-macos.txt")
            self.record_button.setEnabled(False)
            self.status.setToolTip(str(exc))

    def _refresh_microphones(self):
        if self.audio is None:
            return
        try:
            selected = self.microphone.currentData()
            self.microphone.blockSignals(True)
            self.microphone.clear()
            self.microphone.addItem("System default (macOS)", None)
            for index, name, is_default in self.audio.list_input_devices():
                label = name + (" · macOS default" if is_default else "")
                self.microphone.addItem(label, index)
            target = self.microphone.findData(selected)
            self.microphone.setCurrentIndex(target if target >= 0 else 0)
            self.microphone.blockSignals(False)
            self.audio.set_input_device(self.microphone.currentData())
        except Exception as exc:
            self.microphone.blockSignals(False)
            self.audio_hint.setText("Could not list microphones: " + str(exc))

    def _microphone_changed(self, _index):
        if self.audio is None:
            return
        try:
            self.audio.set_input_device(self.microphone.currentData())
            name = self.microphone.currentText()
            self.audio_hint.setText("Microphone: " + name)
        except Exception as exc:
            self.audio_hint.setText("Microphone selection failed: " + str(exc))

    def _check_server(self):
        worker = FunctionWorker(self.ollama.health)
        worker.signals.result.connect(self._server_ok)
        worker.signals.error.connect(lambda e: self.status.setText("Ollama offline — run ollama serve"))
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
        self.transcript.setPlainText(
            f"Loaded: {Path(path).name}\nIndexed {count} searchable sections locally."
        )
        QMessageBox.information(
            self, "Resume ready",
            f"Resume indexed successfully.\n{count} sections added to local search."
        )

    def ask(self):
        question = self.question.text().strip()
        if not question:
            return
        self.ollama.chat_model = self.model.currentText() or "qwen3:8b"
        self.question.clear()
        self._append("You", question)
        self.ask_button.setEnabled(False)
        self.status.setText("Thinking…")
        self._begin_answer_stream()
        worker = FunctionWorker(
            self.generator.answer,
            question,
            list(self.history),
            with_progress=True,
        )
        worker.signals.progress.connect(self._answer_progress)
        worker.signals.result.connect(lambda answer: self._answer_done(question, answer))
        worker.signals.error.connect(self._show_error)
        self.pool.start(worker)

    def _audio_transcript_ready(self, transcript):
        self.transcript.setPlainText(transcript)
        self._append("Live transcript", transcript)
        self.status.setText("Finding relevant context…")
        self.ask_button.setEnabled(False)
        self._begin_answer_stream()
        worker = FunctionWorker(
            self.generator.answer_from_transcript,
            transcript,
            list(self.history),
            with_progress=True,
        )
        worker.signals.progress.connect(self._audio_answer_progress)
        worker.signals.result.connect(self._audio_answer_done)
        worker.signals.error.connect(self._show_error)
        self.pool.start(worker)

    def _answer_progress(self, token):
        self._streamed_answer += token
        self.answer_view.setPlainText(self._streamed_answer)
        cursor = self.answer_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.answer_view.setTextCursor(cursor)
        self.answer_view.ensureCursorVisible()
        self.status.setText("Generating answer…")

    def _audio_answer_progress(self, token):
        self._answer_progress(token)

    def _begin_answer_stream(self):
        self._streamed_answer = ""
        self.answer_view.setPlainText("Generating answer…")

    def _audio_answer_done(self, result):
        transcript, answer = result
        self.transcript.setPlainText(transcript)
        self._append("Copilot", answer)
        self.history.extend([
            {"role": "user", "content": "Live interview transcript:\\n" + transcript},
            {"role": "assistant", "content": answer},
        ])
        self._finish_answer_stream(answer)
        self.ask_button.setEnabled(True)
        self.status.setText("Ready")

    def _recording_changed(self, active):
        self.record_button.setText("Stop recording" if active else "Start recording")
        self.audio_hint.setText("Recording… press ⌃⌥R again to stop" if active else "Transcribing locally…")
        self.microphone.setEnabled(not active)
        self.refresh_microphones_button.setEnabled(not active)
        self.status.setText("Recording mic + system audio…" if active else "Transcribing locally…")

    def _toggle_recording(self):
        if self.audio is not None:
            self.audio.toggle_recording()

    def _audio_error(self, message):
        self.status.setText("Audio error")
        self.audio_hint.setText(message)
        self.record_button.setText("Start recording")

    def _answer_done(self, question, answer):
        self._append("Copilot", answer)
        self.history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        self._finish_answer_stream(answer)
        self.ask_button.setEnabled(True)
        self.status.setText("Ready")

    def _finish_answer_stream(self, answer):
        self.answer_view.setHtml(format_response_html(answer))
        self.answer_view.verticalScrollBar().setValue(
            self.answer_view.verticalScrollBar().maximum()
        )

    def _append(self, speaker, text):
        self.chat.append(
            f"<p style='margin:12px 0 4px 0'><b>{speaker}</b></p>"
            + format_response_html(text)
        )

    def _show_error(self, error):
        self.ask_button.setEnabled(True)
        self.status.setText("Error")
        self.answer_view.setPlainText("Answer generation failed. See the error dialog for details.")
        QMessageBox.critical(self, "Interview Copilot error", error)

    def clear_chat(self):
        self.chat.clear()
        self.answer_view.clear()
        self.transcript.clear()
        self.history.clear()
        self._streamed_answer = ""

    def closeEvent(self, event):
        if self.audio is not None:
            self.audio.shutdown()
        event.accept()
