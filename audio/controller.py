import os
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
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
    overlay_toggle_requested = Signal()
    error = Signal(str)

    def __init__(self, project_root=None):
        super().__init__()
        self.root = Path(project_root or Path(__file__).resolve().parents[1])
        self.temp_root = Path(tempfile.gettempdir())
        self._cleanup_stale_sessions()
        self._session_dir = None
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
        self._hotkey_down = False
        self._overlay_hotkey_down = False
        self._pressed_modifiers = set()
        self.selected_input_device = None  # None means macOS default input

    def _cleanup_stale_sessions(self):
        """Remove abandoned temporary audio folders from crashed app processes."""
        for folder in self.temp_root.glob("interview-copilot-audio-*"):
            try:
                owner_pid = int(folder.name.split("-")[3])
                if owner_pid == os.getpid():
                    continue
                try:
                    os.kill(owner_pid, 0)
                except ProcessLookupError:
                    shutil.rmtree(folder, ignore_errors=True)
                except PermissionError:
                    continue
            except (ValueError, IndexError, OSError):
                continue

    def _remove_session_files(self):
        folder = self._session_dir
        self._session_dir = None
        self._mic_path = None
        self._system_path = None
        if folder is not None:
            shutil.rmtree(folder, ignore_errors=True)

    @property
    def is_recording(self):
        with self._lock:
            return self._recording

    def list_input_devices(self):
        """Return available input devices as (index, name, is_default) tuples."""
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        available = []
        for index, device in enumerate(devices):
            if int(device.get("max_input_channels", 0)) > 0:
                available.append((index, device["name"], index == default_input))
        return available

    def set_input_device(self, device_index=None):
        """Select an input device; None delegates selection to macOS."""
        if self.is_recording:
            raise RuntimeError("Stop recording before changing the microphone.")
        self.selected_input_device = device_index

    def start_hotkey_listener(self):
        if sys.platform != "darwin":
            self.error.emit("Audio capture is currently supported on macOS only.")
            return
        try:
            from pynput import keyboard

            modifiers = {
                keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
            }

            def on_press(key):
                toggle_recording = False
                toggle_overlay = False
                active = False
                with self._lock:
                    if key in modifiers:
                        self._pressed_modifiers.add(key)

                    ctrl_down = any(k in self._pressed_modifiers for k in
                                    (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
                    alt_down = any(k in self._pressed_modifiers for k in
                                   (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r))
                    char = (
                        key.char.lower()
                        if isinstance(key, keyboard.KeyCode) and key.char
                        else None
                    )

                    if ctrl_down and alt_down and char == "r" and not self._hotkey_down:
                        self._hotkey_down = True
                        toggle_recording = True
                        active = self._recording
                    elif ctrl_down and alt_down and char == "h" and not self._overlay_hotkey_down:
                        self._overlay_hotkey_down = True
                        toggle_overlay = True

                if toggle_recording:
                    # Toggle recording with Control + Option + R.
                    if active:
                        self.stop_recording()
                    else:
                        self.start_recording()

                if toggle_overlay:
                    # Emit a Qt signal so the UI toggles on the Qt main thread.
                    self.overlay_toggle_requested.emit()

            def on_release(key):
                with self._lock:
                    if key in modifiers:
                        self._pressed_modifiers.discard(key)
                    if isinstance(key, keyboard.KeyCode) and key.char:
                        char = key.char.lower()
                        if char == "r":
                            self._hotkey_down = False
                        elif char == "h":
                            self._overlay_hotkey_down = False

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as exc:
            self.error.emit(
                "Global shortcuts unavailable. Grant Accessibility/Input "
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
                ["swiftc", "-parse-as-library", str(self.swift_source), "-o", str(binary)],
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
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._session_dir = Path(tempfile.mkdtemp(
                prefix=f"interview-copilot-audio-{os.getpid()}-{uuid.uuid4().hex[:8]}-",
                dir=self.temp_root,
            ))
            self._mic_path = self._session_dir / (stamp + "-mic.wav")
            self._system_path = self._session_dir / (stamp + "-system.m4a")

            self._mic_stream = sd.InputStream(
                device=self.selected_input_device,
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
                process = self._system_process
                return_code = process.poll()
                stderr_text = ""
                if return_code is not None and process.stderr:
                    stderr_text = process.stderr.read().strip()
                detail = line or stderr_text or (
                    "The helper exited before capture started"
                    + (f" (exit code {return_code})" if return_code is not None else ".")
                )
                raise RuntimeError("System audio did not start: " + detail)

            self.recording_changed.emit(True)
        except Exception as exc:
            self._cleanup_capture()
            self._remove_session_files()
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
        mic_path, system_path, session_dir = self._mic_path, self._system_path, self._session_dir
        self._mic_path = None
        self._system_path = None
        self._session_dir = None
        threading.Thread(
            target=self._transcribe,
            args=(mic_path, system_path, session_dir),
            daemon=True,
        ).start()

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
            if process.poll() is None and process.stdin:
                try:
                    process.stdin.write("\\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
                finally:
                    try:
                        process.stdin.close()
                    except (BrokenPipeError, OSError):
                        pass
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            finally:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe is not None:
                        try:
                            pipe.close()
                        except (BrokenPipeError, OSError):
                            pass

    def _transcribe(self, mic_path, system_path, session_dir):
        try:
            results = []
            if mic_path and mic_path.exists():
                mic_text = transcribe_local(mic_path)
                if mic_text:
                    results.append("[YOU / MICROPHONE]\n" + mic_text)
            if system_path and system_path.exists():
                system_text = transcribe_local(system_path)
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
        finally:
            # Keep captured audio only for the local transcription step.
            if session_dir is not None:
                shutil.rmtree(session_dir, ignore_errors=True)

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
