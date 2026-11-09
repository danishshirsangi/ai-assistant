from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTextBrowser,
    QVBoxLayout, QWidget,
)

from core.answer_generator import AnswerGenerator
from core.gemini_client import GeminiClient
from core.resume_rag import ResumeRAG
from ui.macos_window_privacy import set_window_capture_exclusion
from ui.rich_text import format_response_html
from ui.worker import FunctionWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Copilot")
        self.setWindowIcon(
            QIcon(str(Path(__file__).resolve().parents[1] / "assets" / "interview-copilot.svg"))
        )
        # Keep the main application window above other app windows.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1180, 850)
        self.setMinimumSize(900, 650)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #0c1422;
                color: #e8eef8;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            QLabel { color: #e8eef8; background: transparent; }
            QFrame#surfacePanel {
                background: #131f31;
                border: 1px solid #293b55;
                border-radius: 12px;
            }
            QLabel#appTitle { font-size: 23px; font-weight: 750; color: #f4f7ff; }
            QLabel#appSubtitle { font-size: 11px; color: #91a4c0; }
            QLabel#sectionTitle { font-size: 13px; font-weight: 700; color: #c9dafa; }
            QLabel#sectionHint { font-size: 10px; color: #8195b2; }
            QLabel#status {
                color: #b8d5ff;
                background: #1a2e49;
                border: 1px solid #345477;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 650;
            }
            QLineEdit, QComboBox {
                background: #17263a;
                color: #edf4ff;
                border: 1px solid #344a68;
                border-radius: 8px;
                padding: 8px 10px;
                selection-background-color: #4169a5;
                min-height: 18px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #83b2f1; }
            QTextBrowser {
                background: #101b2b;
                color: #eaf1fc;
                border: 1px solid #263a54;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #4169a5;
                font-size: 13px;
            }
            QPushButton {
                background: #263d5d;
                color: #f2f6ff;
                border: 1px solid #405d83;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: 650;
            }
            QPushButton:hover { background: #34547e; }
            QPushButton:pressed { background: #1c2f49; }
            QPushButton:disabled {
                color: #7b8ba2;
                background: #1a2738;
                border-color: #2b3b52;
            }
            QPushButton#primaryButton {
                background: #3975bf;
                border-color: #5792d8;
                color: white;
                padding-left: 17px;
                padding-right: 17px;
            }
            QPushButton#primaryButton:hover { background: #4888d3; }
            QPushButton#recordButton {
                background: #253c5a;
                border-color: #49698e;
                min-width: 112px;
            }
            QPushButton#hideButton {
                background: #1b2a3e;
                border-color: #334b68;
            }
            QSplitter::handle { background: #1d2d43; height: 5px; width: 5px; }
        """)

        self.pool = QThreadPool.globalInstance()
        self.gemini = GeminiClient()
        self.rag = ResumeRAG(self.gemini, persist_dir="vector_db_gemini")
        self.generator = AnswerGenerator(self.gemini, self.rag)
        self.history = []
        self._streamed_answer = ""
        self._capture_privacy_enabled = True
        self.audio = None

        # Render Markdown periodically while streaming instead of rebuilding the
        # entire rich-text document for every token.
        self._stream_render_timer = QTimer(self)
        self._stream_render_timer.setSingleShot(True)
        self._stream_render_timer.setInterval(120)
        self._stream_render_timer.timeout.connect(self._render_streamed_answer)

        self._build_ui()
        self._setup_audio()
        self._check_server()

    def _make_panel(self, title, hint=None):
        panel = QFrame()
        panel.setObjectName("surfacePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(7)

        header = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        header.addWidget(heading)
        header.addStretch()
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("sectionHint")
            header.addWidget(hint_label)
        layout.addLayout(header)
        return panel, layout

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(2)
        title = QLabel("Interview Copilot")
        title.setObjectName("appTitle")
        subtitle = QLabel("Gemini-powered interview assistant")
        subtitle.setObjectName("appSubtitle")
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        self.status = QLabel("Connecting to Gemini…")
        self.status.setObjectName("status")
        header.addWidget(self.status)
        root.addLayout(header)

        # Compact toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        model_label = QLabel("MODEL")
        model_label.setObjectName("sectionHint")
        self.model = QComboBox()
        self.model.addItems(["gemini-3.8-flash"])
        self.model.setMinimumWidth(150)

        upload = QPushButton("Upload resume")
        upload.clicked.connect(self.upload_resume)
        clear = QPushButton("Clear")
        clear.setToolTip("Clear conversation, transcript and latest answer")
        clear.clicked.connect(self.clear_chat)

        self.privacy_button = QPushButton("Capture privacy: ON")
        self.privacy_button.setToolTip(
            "Best-effort request to exclude this window from compatible macOS capture APIs. "
            "This does not guarantee invisibility in meeting apps."
        )
        self.privacy_button.clicked.connect(self._toggle_capture_privacy)

        self.hide_button = QPushButton("Hide window  ⌃⌥H")
        self.hide_button.setObjectName("hideButton")
        self.hide_button.setToolTip(
            "Hide Interview Copilot so you can work in other apps. Press Control + Option + H to restore it."
        )
        self.hide_button.clicked.connect(self._toggle_window_visibility)

        toolbar.addWidget(model_label)
        toolbar.addWidget(self.model)
        toolbar.addWidget(upload)
        toolbar.addWidget(clear)
        toolbar.addWidget(self.privacy_button)
        toolbar.addStretch()
        toolbar.addWidget(self.hide_button)
        root.addLayout(toolbar)

        # Main workspace: source panels on the left, readable live answer on the right.
        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setChildrenCollapsible(False)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        conversation_panel, conversation_layout = self._make_panel(
            "CONVERSATION", "recent turns"
        )
        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setPlaceholderText("Your questions and completed answers will appear here.")
        self.chat.setStyleSheet("font-size: 12px;")
        conversation_layout.addWidget(self.chat, 1)

        transcript_panel, transcript_layout = self._make_panel(
            "LIVE TRANSCRIPT", "local transcription"
        )
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText(
            "After recording stops, the microphone and meeting transcript will appear here."
        )
        self.transcript.setStyleSheet("font-size: 11px; color: #b8c8df;")
        transcript_layout.addWidget(self.transcript, 1)

        left_layout.addWidget(conversation_panel, 3)
        left_layout.addWidget(transcript_panel, 2)

        answer_panel, answer_layout = self._make_panel(
            "LATEST ANSWER", "live response"
        )
        answer_header_hint = QLabel(
            "Formatted response · updates as the model generates"
        )
        answer_header_hint.setObjectName("sectionHint")
        answer_layout.addWidget(answer_header_hint)
        self.answer_view = QTextBrowser()
        self.answer_view.setObjectName("answerView")
        self.answer_view.setOpenExternalLinks(False)
        self.answer_view.setPlaceholderText(
            "Your answer will appear here with headings, bold text, highlights, code and lists."
        )
        self.answer_view.setStyleSheet(
            "QTextBrowser { font-size: 14px; padding: 14px; line-height: 1.5; }"
        )
        answer_layout.addWidget(self.answer_view, 1)

        workspace.addWidget(left_column)
        workspace.addWidget(answer_panel)
        workspace.setSizes([390, 760])
        root.addWidget(workspace, 1)

        # Recording controls
        recording_panel, recording_layout = self._make_panel(
            "AUDIO INPUT", "Control + Option + R to start / stop"
        )
        recording_row = QHBoxLayout()
        self.record_button = QPushButton("Start recording")
        self.record_button.setObjectName("recordButton")
        self.record_button.setToolTip(
            "Press Control + Option + R to start recording; press again to stop."
        )
        self.record_button.clicked.connect(self._toggle_recording)

        microphone_label = QLabel("Microphone")
        microphone_label.setObjectName("sectionHint")
        self.microphone = QComboBox()
        self.microphone.setMinimumWidth(220)
        self.microphone.setToolTip("Choose the microphone used for your voice.")
        self.microphone.addItem("System default (macOS)", None)
        self.refresh_microphones_button = QPushButton("Refresh")
        self.refresh_microphones_button.setToolTip("Refresh available microphones.")
        self.refresh_microphones_button.clicked.connect(self._refresh_microphones)

        self.audio_hint = QLabel("Mic + system audio · local transcription")
        self.audio_hint.setObjectName("sectionHint")

        recording_row.addWidget(self.record_button)
        recording_row.addSpacing(8)
        recording_row.addWidget(microphone_label)
        recording_row.addWidget(self.microphone)
        recording_row.addWidget(self.refresh_microphones_button)
        recording_row.addStretch()
        recording_row.addWidget(self.audio_hint)
        recording_layout.addLayout(recording_row)
        root.addWidget(recording_panel)

        # Typed question composer
        composer = QHBoxLayout()
        composer.setSpacing(9)
        self.question = QLineEdit()
        self.question.setPlaceholderText(
            "Ask an interview, SQL, Python or data engineering question…"
        )
        self.question.returnPressed.connect(self.ask)
        self.ask_button = QPushButton("Generate answer")
        self.ask_button.setObjectName("primaryButton")
        self.ask_button.clicked.connect(self.ask)
        composer.addWidget(self.question, 1)
        composer.addWidget(self.ask_button)
        root.addLayout(composer)

        footer = QLabel(
            "⌃⌥R  Record / stop     ·     ⌃⌥H  Hide / restore window     ·     Local AI processing"
        )
        footer.setObjectName("sectionHint")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

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
                "Could not apply the capture privacy request: " + detail +
                "\nMeeting-app behaviour varies; this is not a universal guarantee."
            )
        else:
            self.privacy_button.setToolTip(
                "The main window is set to " +
                ("exclude from" if enabled else "allow") +
                " compatible macOS capture APIs. Meeting-app behaviour varies."
            )

    def _toggle_window_visibility(self):
        """Hide or restore the main window without touching audio or workers."""
        if self.isVisible():
            self.hide()
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _setup_audio(self):
        try:
            from audio.controller import AudioController

            self.audio = AudioController()
            self.audio.recording_changed.connect(self._recording_changed)
            self.audio.transcript_ready.connect(self._audio_transcript_ready)
            self.audio.window_visibility_toggle_requested.connect(
                self._toggle_window_visibility
            )
            self.audio.error.connect(self._audio_error)
            self.microphone.currentIndexChanged.connect(self._microphone_changed)
            self._refresh_microphones()
            self.audio.start_hotkey_listener()
            self.audio_hint.setText("⌃⌥R record · ⌃⌥H hide / restore window")
        except Exception as exc:
            self.audio_hint.setText(
                "Audio dependencies unavailable. Install requirements-audio-macos.txt"
            )
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
            self.audio_hint.setText("Microphone: " + self.microphone.currentText())
        except Exception as exc:
            self.audio_hint.setText("Microphone selection failed: " + str(exc))

    def _check_server(self):
        worker = FunctionWorker(self.gemini.health)
        worker.signals.result.connect(self._gemini_ok)
        worker.signals.error.connect(
            lambda error: self._gemini_unavailable(error)
        )
        self.pool.start(worker)

    def _gemini_unavailable(self, error):
        message = str(error)
        if "API key not found" in message:
            self._set_status("Gemini API key missing — configure .env", warning=True)
        else:
            self._set_status("Gemini unavailable — check connection / key", warning=True)
        self.status.setToolTip(message)

    def _set_status(self, text, warning=False):
        self.status.setText(text)
        self.status.setStyleSheet(
            "color: #ffd58a; background: #382c1b; border: 1px solid #75552b; "
            "border-radius: 10px; padding: 5px 10px;"
            if warning else ""
        )

    def _server_ok(self, data):
        self._set_status("Gemini connected")
        names = [model.get("name") for model in data.get("models", []) if model.get("name")]
        if names:
            self.model.clear()
            self.model.addItems(names)
            if self.gemini.chat_model in names:
                self.model.setCurrentText(self.gemini.chat_model)

    def upload_resume(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select resume", str(Path.home()),
            "Documents (*.pdf *.docx *.txt *.md)"
        )
        if not path:
            return
        self._set_status("Embedding resume with Gemini…")
        worker = FunctionWorker(self.rag.add_file, path)
        worker.signals.result.connect(lambda count: self._resume_done(path, count))
        worker.signals.error.connect(self._show_error)
        self.pool.start(worker)

    def _resume_done(self, path, count):
        self._set_status("Resume indexed with Gemini")
        self._append("Resume", f"Loaded **{Path(path).name}** · indexed {count} searchable sections.")
        QMessageBox.information(
            self, "Resume ready",
            f"Resume indexed successfully.\n{count} sections added to local search."
        )

    def ask(self):
        question = self.question.text().strip()
        if not question:
            return
        self.gemini.chat_model = self.model.currentText() or GeminiClient.DEFAULT_CHAT_MODEL
        self.question.clear()
        self._append("You", question)
        self.ask_button.setEnabled(False)
        self._set_status("Thinking…")
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
        self.ask_button.setEnabled(False)
        self._set_status("Finding relevant context…")
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
        self._set_status("Generating answer…")
        if not self._stream_render_timer.isActive():
            self._stream_render_timer.start()

    def _audio_answer_progress(self, token):
        self._answer_progress(token)

    def _begin_answer_stream(self):
        self._stream_render_timer.stop()
        self._streamed_answer = ""
        self.answer_view.setHtml(
            "<p style='color:#9fb7d6;'>Generating answer…</p>"
        )

    def _render_streamed_answer(self):
        if not self._streamed_answer:
            return
        scrollbar = self.answer_view.verticalScrollBar()
        keep_at_bottom = scrollbar.value() >= scrollbar.maximum() - 8
        self.answer_view.setHtml(format_response_html(self._streamed_answer))
        if keep_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _finish_answer_stream(self, answer):
        self._stream_render_timer.stop()
        self._streamed_answer = answer
        self.answer_view.setHtml(format_response_html(answer))
        self.answer_view.verticalScrollBar().setValue(
            self.answer_view.verticalScrollBar().maximum()
        )

    def _audio_answer_done(self, result):
        transcript, answer = result
        self.transcript.setPlainText(transcript)
        self._append("Copilot", answer)
        self.history.extend([
            {"role": "user", "content": "Live interview transcript:\n" + transcript},
            {"role": "assistant", "content": answer},
        ])
        self._finish_answer_stream(answer)
        self.ask_button.setEnabled(True)
        self._set_status("Ready")

    def _recording_changed(self, active):
        self.record_button.setText("Stop recording" if active else "Start recording")
        self.audio_hint.setText(
            "Recording · ⌃⌥R stop · ⌃⌥H hide window"
            if active else "Transcribing locally…"
        )
        self.microphone.setEnabled(not active)
        self.refresh_microphones_button.setEnabled(not active)
        self._set_status(
            "Recording mic + system audio…" if active else "Transcribing locally…"
        )

    def _toggle_recording(self):
        if self.audio is not None:
            self.audio.toggle_recording()

    def _audio_error(self, message):
        self._set_status("Audio error", warning=True)
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
        self._set_status("Ready")

    def _append(self, speaker, text):
        self.chat.append(
            f"<p style='margin:9px 0 3px;color:#a9ccff;'><b>{speaker}</b></p>"
            + format_response_html(text)
        )
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _show_error(self, error):
        self._stream_render_timer.stop()
        self.ask_button.setEnabled(True)
        self._set_status("Error", warning=True)
        self.answer_view.setHtml(
            "<p style='color:#ffb4a8;'>Answer generation failed. See the error dialog for details.</p>"
        )
        QMessageBox.critical(self, "Interview Copilot error", error)

    def clear_chat(self):
        self.chat.clear()
        self.answer_view.clear()
        self.transcript.clear()
        self.history.clear()
        self._streamed_answer = ""
        self._stream_render_timer.stop()
        self._set_status("Ready")

    def closeEvent(self, event):
        self._stream_render_timer.stop()
        if self.audio is not None:
            self.audio.shutdown()
        event.accept()
