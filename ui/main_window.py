import re
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTextBrowser,
    QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
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
        self.setWindowTitle("AI Meeting Assistant")
        self.setWindowIcon(
            QIcon(str(Path(__file__).resolve().parents[1] / "assets" / "interview-copilot.svg"))
        )
        # Keep the main application window above other app windows.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1180, 850)
        self.setMinimumSize(900, 650)

        # Glass-inspired black and green theme.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
                color: #ecf7ef;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            }
            QWidget {
                color: #ecf7ef;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                background: transparent;
            }
            QWidget#appRoot {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #050806, stop:0.52 #09110c, stop:1 #0b1710);
                border: 1px solid rgba(125, 255, 155, 38);
                border-radius: 22px;
            }
            QLabel { color: #ecf7ef; background: transparent; }
            QFrame#surfacePanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(21, 34, 25, 232), stop:1 rgba(10, 19, 13, 224));
                border: 1px solid rgba(143, 255, 171, 52);
                border-top: 1px solid rgba(190, 255, 205, 78);
                border-radius: 17px;
            }
            QLabel#appTitle { font-size: 25px; font-weight: 800; color: #f4fff6; }
            QLabel#appSubtitle { font-size: 11px; color: #8aa993; }
            QLabel#sectionTitle {
                font-size: 11px; font-weight: 800; letter-spacing: 1.1px;
                color: #b9eac4;
            }
            QLabel#sectionHint { font-size: 10px; color: #789181; }
            QLabel#status {
                color: #a9f5b8; background: rgba(37, 113, 58, 60);
                border: 1px solid rgba(101, 239, 132, 90);
                border-radius: 12px; padding: 7px 12px;
                font-size: 11px; font-weight: 700;
            }
            QLineEdit, QComboBox {
                background: rgba(10, 22, 14, 225); color: #effff2;
                border: 1px solid rgba(119, 216, 140, 76);
                border-radius: 11px; padding: 9px 12px;
                selection-background-color: #267b3f; min-height: 19px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #69e985; background: rgba(15, 32, 19, 240);
            }
            QComboBox::drop-down { border: none; width: 25px; }
            QComboBox QAbstractItemView {
                background: #0c1710; color: #eaffee;
                selection-background-color: #225e34;
                border: 1px solid #326d41; outline: none;
            }
            QListWidget {
                background: rgba(7, 16, 10, 205); color: #cfe9d4;
                border: 1px solid rgba(112, 200, 132, 50);
                border-radius: 12px; padding: 7px; outline: none; font-size: 12px;
            }
            QListWidget::item {
                padding: 12px 10px; margin: 3px 1px;
                border-radius: 9px; border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background: rgba(57, 120, 70, 65);
                border: 1px solid rgba(115, 222, 139, 45);
            }
            QListWidget::item:selected {
                background: rgba(52, 158, 78, 76); color: #f4fff6;
                border: 1px solid rgba(126, 244, 150, 135);
            }
            QTextBrowser {
                background: rgba(6, 14, 9, 190); color: #e9f5eb;
                border: 1px solid rgba(112, 200, 132, 56);
                border-radius: 12px; padding: 14px;
                selection-background-color: #267b3f; font-size: 13px;
            }
            QPushButton {
                background: rgba(20, 37, 25, 220); color: #dff5e3;
                border: 1px solid rgba(123, 214, 143, 72);
                border-radius: 11px; padding: 9px 14px;
                font-size: 11px; font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(41, 83, 49, 238);
                border-color: rgba(137, 245, 158, 145);
            }
            QPushButton:pressed { background: rgba(25, 67, 35, 245); }
            QPushButton:disabled {
                color: #617568; background: rgba(17, 26, 19, 170);
                border-color: rgba(95, 126, 101, 40);
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8af59c, stop:1 #39c65f);
                border: 1px solid #a6ffb3; color: #06110a;
                font-weight: 800; padding-left: 18px; padding-right: 18px;
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a1ffae, stop:1 #58dc78);
            }
            QPushButton#recordButton {
                background: rgba(38, 105, 54, 90);
                border-color: rgba(111, 236, 137, 145);
                color: #c8ffd2; min-width: 112px;
            }
            QPushButton#recordButton[recording="true"] {
                background: rgba(139, 40, 40, 210);
                border-color: #ff7979; color: #fff2f2;
            }
            QPushButton#hideButton {
                background: rgba(9, 18, 12, 205);
                border-color: rgba(118, 198, 134, 60); color: #a9c9b0;
            }
            QSplitter::handle {
                background: rgba(108, 213, 131, 72);
                width: 5px; margin: 5px 0; border-radius: 2px;
            }
        """)

        self.pool = QThreadPool.globalInstance()
        self._active_workers = set()
        self.gemini = GeminiClient()
        self.rag = ResumeRAG(self.gemini, persist_dir="vector_db_gemini")
        self.generator = AnswerGenerator(self.gemini, self.rag)
        self.history = []
        self.question_items = {}
        self._next_question_id = 1
        self._active_question_id = None
        self._selected_question_id = None
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
        central.setObjectName("appRoot")
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(2)
        title = QLabel("AI Meeting Assistant")
        title.setObjectName("appTitle")
        subtitle = QLabel("Your live meeting and interview copilot")
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
        self.model.addItems([GeminiClient.DEFAULT_CHAT_MODEL])
        self.model.setMinimumWidth(150)

        upload = QPushButton("Upload resume")
        upload.clicked.connect(self.upload_resume)
        clear = QPushButton("Clear")
        clear.setText("Clear session")
        clear.setToolTip("Clear the question list, answers and session context")
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
            "Hide AI Meeting Assistant. Press Control + Option + H to restore it."
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
        left_layout.setSpacing(12)

        questions_panel, questions_layout = self._make_panel(
            "QUESTIONS", "select one to revisit its answer"
        )
        self.questions_empty = QLabel("Questions will appear here as you ask them.")
        self.questions_empty.setObjectName("sectionHint")
        self.questions_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_list = QListWidget()
        self.question_list.setSpacing(2)
        self.question_list.currentItemChanged.connect(self._show_selected_question)
        questions_layout.addWidget(self.questions_empty)
        questions_layout.addWidget(self.question_list, 1)
        left_layout.addWidget(questions_panel, 1)

        answer_panel, answer_layout = self._make_panel(
            "ANSWER", "latest response"
        )
        self.answer_header_hint = QLabel(
            "Your latest answer will appear here. Select a question to revisit its answer."
        )
        self.answer_header_hint.setObjectName("sectionHint")
        self.answer_header_hint.setWordWrap(True)
        answer_layout.addWidget(self.answer_header_hint)
        self.answer_view = QTextBrowser()
        self.answer_view.setObjectName("answerView")
        self.answer_view.setOpenExternalLinks(False)
        self.answer_view.setPlaceholderText(
            "Your latest answer will appear here with headings, code and formatted content."
        )
        self.answer_view.setStyleSheet(
            "QTextBrowser { font-size: 14px; padding: 18px; line-height: 1.55; border-radius: 14px; }"
        )
        answer_layout.addWidget(self.answer_view, 1)

        workspace.addWidget(left_column)
        workspace.addWidget(answer_panel)
        workspace.setSizes([320, 830])
        root.addWidget(workspace, 1)

        # Recording controls
        recording_panel, recording_layout = self._make_panel(
            "AUDIO INPUT", "⌃⌥R to toggle recording"
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

        self.audio_hint = QLabel("Mic + system audio · transcribed on device")
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
            "⌃⌥R  Record / stop     ·     ⌃⌥H  Hide / restore window     ·     Local transcription · Gemini responses online"
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

    def _start_worker(self, worker):
        # QRunnable auto-deletion is disabled; keep the Python wrapper and its
        # signal object alive until the worker has posted all result/error events.
        self._active_workers.add(worker)
        worker.signals.finished.connect(self._release_worker)
        self.pool.start(worker)

    def _release_worker(self, worker):
        self._active_workers.discard(worker)

    def _check_server(self):
        worker = FunctionWorker(self.gemini.health)
        worker.signals.result.connect(self._gemini_ok)
        worker.signals.error.connect(
            lambda error: self._gemini_unavailable(error)
        )
        self._start_worker(worker)

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

    def _gemini_ok(self, data):
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
        self._start_worker(worker)

    def _resume_done(self, path, count):
        self._set_status("Resume indexed with Gemini")
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
        question_id = self._add_question(question)
        self._active_question_id = question_id
        self.ask_button.setEnabled(False)
        self._set_status("Preparing Gemini response…")
        self._begin_answer_stream(question_id)
        worker = FunctionWorker(
            self.generator.answer,
            question,
            list(self.history),
            with_progress=True,
            with_stage=True,
        )
        worker.signals.stage.connect(self._answer_stage)
        worker.signals.progress.connect(self._answer_progress)
        worker.signals.result.connect(
            lambda answer, qid=question_id: self._answer_done(qid, question, answer)
        )
        worker.signals.error.connect(
            lambda error, qid=question_id: self._question_error(qid, error)
        )
        self._start_worker(worker)

    @staticmethod
    def _question_label_from_transcript(transcript):
        source = transcript
        marker = "[OTHER PARTICIPANTS / SYSTEM AUDIO]"
        if marker in transcript:
            source = transcript.split(marker, 1)[1]
        sentences = [
            part.strip()
            for part in re.split(r"(?<=[?.!])\s+", source)
            if part.strip()
        ]
        questions = [part for part in sentences if part.endswith("?")]
        label = questions[-1] if questions else (sentences[-1] if sentences else source.strip())
        label = " ".join(label.split())
        if not label:
            label = "Interview recording"
        return label[:117].rstrip() + ("…" if len(label) > 120 else "")

    def _audio_transcript_ready(self, transcript):
        question = self._question_label_from_transcript(transcript)
        question_id = self._add_question(question)
        self._active_question_id = question_id
        self.ask_button.setEnabled(False)
        self._set_status("Finding relevant context…")
        self._begin_answer_stream(question_id)
        worker = FunctionWorker(
            self.generator.answer_from_transcript,
            transcript,
            list(self.history),
            with_progress=True,
            with_stage=True,
        )
        worker.signals.stage.connect(self._answer_stage)
        worker.signals.progress.connect(self._audio_answer_progress)
        worker.signals.result.connect(
            lambda result, qid=question_id, label=question:
                self._audio_answer_done(qid, label, result)
        )
        worker.signals.error.connect(
            lambda error, qid=question_id: self._question_error(qid, error)
        )
        self._start_worker(worker)

    def _add_question(self, question):
        question = " ".join(str(question).split())
        question_id = self._next_question_id
        self._next_question_id += 1
        self.question_items[question_id] = {
            "question": question,
            "answer": "",
            "status": "pending",
        }
        visible = question if len(question) <= 105 else question[:102].rstrip() + "…"
        item = QListWidgetItem(f"Q{question_id:02d}  {visible}")
        item.setData(Qt.ItemDataRole.UserRole, question_id)
        item.setToolTip(question)
        self.question_list.addItem(item)
        self.questions_empty.hide()
        self.question_list.setCurrentItem(item)
        self.question_list.scrollToBottom()
        return question_id

    def _show_selected_question(self, current, _previous):
        if current is None:
            self._selected_question_id = None
            return
        question_id = current.data(Qt.ItemDataRole.UserRole)
        entry = self.question_items.get(question_id)
        if entry is None:
            return
        self._selected_question_id = question_id
        question = entry["question"]
        self.answer_header_hint.setText(question)
        self.answer_header_hint.setToolTip(question)
        if entry["status"] == "pending":
            self.answer_view.setHtml(
                "<p style='color:#9fb7d6;'>Generating answer…</p>"
            )
        elif entry["status"] == "error":
            self.answer_view.setHtml(
                "<p style='color:#ffb4a8;'>This answer could not be generated.</p>"
            )
        elif entry["answer"]:
            self.answer_view.setHtml(format_response_html(entry["answer"]))
        else:
            self.answer_view.clear()

    def _question_error(self, question_id, error):
        entry = self.question_items.get(question_id)
        if entry is not None:
            entry["status"] = "error"
        self._stream_render_timer.stop()
        self.ask_button.setEnabled(True)
        self._set_status("Error", warning=True)
        if self._selected_question_id == question_id:
            self.answer_view.setHtml(
                "<p style='color:#ffb4a8;'>Answer generation failed. See the error dialog for details.</p>"
            )
        QMessageBox.critical(self, "AI Meeting Assistant error", str(error))

    def _answer_stage(self, stage):
        self._set_status(stage)

    def _answer_progress(self, token):
        self._streamed_answer += token
        self._set_status("Generating answer…")
        if self._selected_question_id == self._active_question_id:
            if not self._stream_render_timer.isActive():
                self._stream_render_timer.start()

    def _audio_answer_progress(self, token):
        self._answer_progress(token)

    def _begin_answer_stream(self, question_id):
        self._stream_render_timer.stop()
        self._streamed_answer = ""
        if self._selected_question_id == question_id:
            self.answer_header_hint.setText(
                self.question_items[question_id]["question"]
            )
            self.answer_view.setHtml(
                "<p style='color:#9fb7d6;'>Generating answer…</p>"
            )

    def _render_streamed_answer(self):
        if not self._streamed_answer:
            return
        if self._selected_question_id != self._active_question_id:
            return
        scrollbar = self.answer_view.verticalScrollBar()
        keep_at_bottom = scrollbar.value() >= scrollbar.maximum() - 8
        self.answer_view.setHtml(format_response_html(self._streamed_answer))
        if keep_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _finish_answer_stream(self, question_id, answer):
        self._stream_render_timer.stop()
        entry = self.question_items.get(question_id)
        if entry is not None:
            entry["answer"] = answer
            entry["status"] = "complete"
        self._streamed_answer = answer
        if self._selected_question_id == question_id:
            self.answer_header_hint.setText(entry["question"] if entry else "Answer")
            self.answer_view.setHtml(format_response_html(answer))
            self.answer_view.verticalScrollBar().setValue(
                self.answer_view.verticalScrollBar().maximum()
            )

    def _audio_answer_done(self, question_id, question, result):
        transcript, answer = result
        self.history.extend([
            {"role": "user", "content": "Live interview transcript:\n" + transcript},
            {"role": "assistant", "content": answer},
        ])
        self._finish_answer_stream(question_id, answer)
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

    def _answer_done(self, question_id, question, answer):
        self.history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        self._finish_answer_stream(question_id, answer)
        self.ask_button.setEnabled(True)
        self._set_status("Ready")

    def _show_error(self, error):
        self._stream_render_timer.stop()
        self.ask_button.setEnabled(True)
        self._set_status("Error", warning=True)
        QMessageBox.critical(self, "AI Meeting Assistant error", str(error))

    def clear_chat(self):
        self.question_list.clear()
        self.question_items.clear()
        self._next_question_id = 1
        self._active_question_id = None
        self._selected_question_id = None
        self.questions_empty.show()
        self.answer_view.clear()
        self.answer_header_hint.setText(
            "Your latest answer will appear here. Select a question to revisit its answer."
        )
        self.history.clear()
        self._streamed_answer = ""
        self._stream_render_timer.stop()
        self._set_status("Ready")

    def closeEvent(self, event):
        self._stream_render_timer.stop()
        if self.audio is not None:
            self.audio.shutdown()
        event.accept()
