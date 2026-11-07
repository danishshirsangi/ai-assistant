import select
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, Signal

from audio.transcriber import transcribe_local


class AudioController(QObject):
    recording_changed = Signal(bool)
    transcript_ready = Signal(str)
    error = Signal(str)

    def __init__(self, project_root=None):
        super().__init__()
        self.root = Path(project_root or Path(__file__).resolve().parents[1])
        self.sessions = self.root / "data" / "audio_sessions"
        self.binary_dir = self.root / "data" / "bin"
        self.swift_source = self.root / "audio" / "macos_system_audio.swift"
        self._lock = threading.RLock()
        self._recording = False
        self._mic_stream = None
        self._mic_frames = []
        self._system_process = None
        self._mic_path = None
        self._system_path = None
        self._listener = None
        self._control_down = False

    @property
    def is_recording(self):
        with self._lock:
            return self._recording

    def start_hotkey_listener(self):
        if sys.platform != "darwin":
            self.error.emit("Audio capture is currently supported on macOS only.")
            return
        try:
            from pynput import keyboard

            def on_press(key):
                if key not in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    return
                with self._lock:
                    if self._control_down:
                        return
                    self._control_down = True
                self.start_recording()

            def on_release(key):
                if key not in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    return
                with self._lock:
                    self._control_down = False
                    active = self._recording
                if active:
                    self.stop_recording()

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as exc:
            self.error.emit(
                "Global Control shortcut unavailable. Grant Accessibility/Input "
                "Monitoring permission or use the in-app recording button. " + str(exc)
            )

    def _compile_helper(self):
        if sys.platform != "darwin":
            raise RuntimeError("System audio capture requires macOS.")
        if not self.swift_source.exists():
            raise RuntimeError("Missing audio/macos_system_audio.swift.")
        self.binary_dir.mkdir(parents=True, exist_ok=True)
        binary = self.binary_dir / "system_audio_capture"
        if binary.exists() and binary.stat().st_mtime >= self.swift_source.stat().st_mtime:
            return binary
        try:
            result = subprocess.run(
                ["swiftc", str(self.swift_source), "-o", str(binary)],
                capture_output=True, text=True, timeout=120,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Install Xcode Command Line Tools: xcode-select --install") from exc
        if result.returncode:
            raise RuntimeError("Swift ScreenCaptureKit compile failed:\n" + result.stderr[-2500:])
        return binary

    def start_recording(self):
        with self._lock:
            if self._recording:
                return
            self._recording = True
            self._mic_frames = []
        try:
            self.sessions.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._mic_path = self.sessions / (stamp + "-mic.wav")
            self._system_path = self.sessions / (stamp + "-system.m4a")

            self._mic_stream = sd.InputStream(
                samplerate=48000, channels=1, dtype="int16",
                callback=self._mic_callback,
            )
            self._mic_stream.start()

            binary = self._compile_helper()
            self._system_process = subprocess.Popen(
                [str(binary), str(self._system_path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1,
            )
            ready, _, _ = select.select([self._system_process.stdout], [], [], 20)
            if not ready:
                raise RuntimeError("Timed out starting ScreenCaptureKit system audio.")
            line = self._system_process.stdout.readline().strip()
            if line != "READY":
                detail = line or "The helper exited before capture started."
                raise RuntimeError("System audio did not start: " + detail)

            self.recording_changed.emit(True)
        except Exception as exc:
            self._cleanup_capture()
            with self._lock:
                self._recording = False
            self.error.emit(str(exc))

    def _mic_callback(self, indata, frames, timing, status):
        self._mic_frames.append(indata.copy())

    def stop_recording(self):
        with self._lock:
            if not self._recording:
                return
            self._recording = False
        self._cleanup_capture()
        self.recording_changed.emit(False)
        threading.Thread(target=self._transcribe, daemon=True).start()

    def _cleanup_capture(self):
        if self._mic_stream is not None:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

        if self._mic_frames and self._mic_path:
            try:
                sf.write(
                    str(self._mic_path), np.concatenate(self._mic_frames, axis=0),
                    48000, subtype="PCM_16",
                )
            except Exception as exc:
                self.error.emit("Could not save microphone audio: " + str(exc))
        self._mic_frames = []

        process = self._system_process
        self._system_process = None
        if process is not None:
            try:
                if process.stdin:
                    process.stdin.write("\n")
                    process.stdin.flush()
                    process.stdin.close()
                process.wait(timeout=25)
            except Exception:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except Exception:
                    process.kill()

    def _transcribe(self):
        try:
            results = []
            if self._mic_path and self._mic_path.exists():
                mic_text = transcribe_local(self._mic_path)
                if mic_text:
                    results.append("[YOU / MICROPHONE]\n" + mic_text)
            if self._system_path and self._system_path.exists():
                system_text = transcribe_local(self._system_path)
                if system_text:
                    results.append("[OTHER PARTICIPANTS / SYSTEM AUDIO]\n" + system_text)
            transcript = "\n\n".join(results).strip()
            if not transcript:
                raise RuntimeError(
                    "No speech detected. Check Microphone and Screen & System Audio "
                    "Recording permissions, then try again."
                )
            self.transcript_ready.emit(transcript)
        except Exception as exc:
            self.error.emit("Local transcription failed: " + str(exc))

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def shutdown(self):
        if self.is_recording:
            self.stop_recording()
        if self._listener is not None:
            self._listener.stop()
